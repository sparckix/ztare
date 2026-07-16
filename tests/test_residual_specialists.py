"""Tests for residual_specialists — no LLM dispatches; dispatch is monkeypatched."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest

from ztare.fit.mdl import description_units
from ztare.worldmodel.residual_specialists import (
    RECEIPT_SCHEMA,
    build_frontier,
    build_shards,
    specialist_briefing,
    run_specialists,
    _partition_too_fine,
    _information_yield,
    _parse_mechanism,
    _parse_discriminator,
    _append_refuted_mechanism,
    _append_form_error_receipt,
    _normalize_patch_base_sha,
    _patch_base_directive,
    _stage_specialist_pack,
    _specialist_mode,
)
from ztare.validator.worldmodel_typed_payload import WORLDMODEL_TYPED_PAYLOAD_CONTRACT_PROMPT


# ── Fixtures ───────────────────────────────────────────────────────────────


def _make_project(tmp_path: Path, records: list[dict] | None = None) -> Path:
    """Create a minimal project dir with candidate_memory.json."""
    proj = tmp_path / "projects" / "test_proj"
    ws = proj / "workspace"
    ws.mkdir(parents=True)
    if records is None:
        records = _two_class_records()
    cm = {"records": records}
    (ws / "candidate_memory.json").write_text(json.dumps(cm), encoding="utf-8")
    # champion stub
    (proj / "test_model.py").write_text("# stub\ndef solve(grid): return grid\n", encoding="utf-8")
    return proj


def _make_record(row: int, col: int, t: int = 0, claim_class: str = "cls_A") -> dict:
    return {
        "claim_class": claim_class,
        "sha": f"sha_{row}_{col}_{t}",
        "holdout_depth": 1,
        "counterexample_trace": {
            "t": t,
            "action": "paint",
            "predicted": 0,
            "observed": 1,
            "holdout_witness": {
                "t": t,
                "action": "paint",
                "step_index": 0,
                "divergent_cells": [{"row": row, "col": col, "predicted": 0, "actual": 1}],
            },
        },
    }


def _two_class_records() -> list[dict]:
    # class A: cells at (0,0)
    # class B: cells at (3,3)
    return [
        _make_record(0, 0, t=5, claim_class="cls_A"),
        _make_record(0, 0, t=7, claim_class="cls_A"),
        _make_record(3, 3, t=10, claim_class="cls_B"),
        _make_record(3, 3, t=12, claim_class="cls_B"),
    ]


def _make_project_with_champion(tmp_path: Path) -> Path:
    """Create a project with champion_materialization.jsonl pointing to a record in candidate_memory."""
    proj = tmp_path / "projects" / "champ_proj"
    ws = proj / "workspace"
    ws.mkdir(parents=True)

    # Plant a champion record with a known sha and holdout_witness
    records = [
        {
            "sha": "abc12345",
            "holdout_depth": 3,
            "counterexample_trace": {
                "holdout_witness": {
                    "t": 7,
                    "action": 1,
                    "step_index": 2,
                    "divergent_cells": [
                        {"row": 5, "col": 5, "predicted": 0, "actual": 3},
                    ],
                },
            },
        },
        _make_record(1, 1, t=1, claim_class="other"),
    ]
    (ws / "candidate_memory.json").write_text(json.dumps({"records": records}), encoding="utf-8")

    # champion_materialization.jsonl pointing to sha abc12345
    mat_row = {
        "schema": "champion_materialization_v1",
        "promoted_sha": "abc12345",
        "from_ref": "workspace/submissions/iter_001.py",
        "gate_summary_after": {"gated_sha256": "abc12345", "score": 0.9},
        "ts": "20260711T000000",
    }
    (ws / "champion_materialization.jsonl").write_text(json.dumps(mat_row) + "\n", encoding="utf-8")

    (proj / "test_model.py").write_text("# champion\ndef solve(grid): return grid\n", encoding="utf-8")
    return proj


# ── Test 1: two synthetic classes → 2 shards (legacy --by-cells) ──────────


def test_build_shards_two_classes(tmp_path):
    proj = _make_project(tmp_path)
    shards = build_shards(proj, max_shards=4, by_cells=True)
    assert len(shards) == 2, f"expected 2 shards, got {len(shards)}: {[s['class_id'] for s in shards]}"
    # ranked by yield_bits descending
    assert shards[0]["yield_bits"] >= shards[1]["yield_bits"]


def test_information_yield_prices_the_match_partition():
    records = _two_class_records()
    assert _information_yield([{"row": 0, "col": 0}], records) == 1.0
    assert _information_yield([{"row": 8, "col": 8}], records) == 0.0
    assert _information_yield(
        [{"row": 0, "col": 0}, {"row": 3, "col": 3}], records
    ) == 0.0


# ── Test 2: briefing content + size ───────────────────────────────────────


def test_briefing_content_and_size(tmp_path):
    proj = _make_project(tmp_path)
    shards = build_shards(proj, max_shards=4)
    shard = shards[0]
    briefing = specialist_briefing(shard, proj)

    # must contain PATCH_BASE directive
    assert "PATCH_BASE" in briefing
    # must contain contract prompt verbatim
    assert WORLDMODEL_TYPED_PAYLOAD_CONTRACT_PROMPT[:50] in briefing
    # must contain class_id
    assert shard["class_id"] in briefing
    # size roughly 4–10k chars (not tiny, not huge)
    assert 500 <= len(briefing) <= 20_000, f"briefing len={len(briefing)}"
    # must contain FRONTIER section
    assert "FRONTIER" in briefing
    # must contain ELIMINATED FAMILIES section
    assert "ELIMINATED FAMILIES" in briefing
    # must contain THE JOB section
    assert "THE JOB" in briefing
    # must reference MECHANISM: and DISCRIMINATOR: in THE JOB
    assert "MECHANISM:" in briefing
    assert "DISCRIMINATOR:" in briefing


# ── Test 3: degenerate — no witness records ────────────────────────────────


def test_build_shards_empty_project(tmp_path):
    proj = _make_project(tmp_path, records=[])
    # mechanism sharding (default): bootstrap → 2 lane shards
    shards = build_shards(proj, max_shards=4)
    assert len(shards) == 2
    lanes = {s["lane"] for s in shards}
    assert lanes == {"lane_a", "lane_b"}


# ── Test 4: dry_run → no dispatch ─────────────────────────────────────────


def test_dry_run_no_dispatch(tmp_path):
    proj = _make_project(tmp_path)
    with patch("ztare.worldmodel.residual_specialists.dispatch_model") as mock_dispatch:
        result = run_specialists(proj, dry_run=True)
    mock_dispatch.assert_not_called()
    assert result["dry_run"] is True
    assert "shards" in result
    assert "briefings" in result


# ── Test 5: submission filenames use submissions/specialist_<class_id>_<n>.py


def test_submission_filename(tmp_path):
    proj = _make_project(tmp_path)
    shards = build_shards(proj, max_shards=1)
    shard = shards[0]
    cid = shard["class_id"]

    fake_code = "def solve(grid): return grid\n"
    fake_payload = json.dumps({
        "test_model_py": fake_code,
        "thesis_markdown": "MECHANISM: timer under-clears\nDISCRIMINATOR: observe t==5 cell",
        "control_receipts": {},
    })
    fake_dispatch = SimpleNamespace(returncode=0, text=fake_payload)

    with patch("ztare.worldmodel.residual_specialists.dispatch_model", return_value=fake_dispatch):
        with patch("ztare.worldmodel.residual_specialists._gate_candidates", return_value=[
            {"candidate": str(proj / "workspace" / "submissions" / f"specialist_{cid}_0.py"),
             "visible_exact": 1, "visible_total": 1, "holdout_depth": 0, "holdout_total": 0,
             "load_error": None, "grid_dsl_expressible": True, "grid_dsl_size": 10}
        ]):
            result = run_specialists(proj, dry_run=False)

    sub_dir = proj / "workspace" / "submissions"
    written = list(sub_dir.glob(f"specialist_{cid}_*.py"))
    assert len(written) >= 1
    assert written[0].name.startswith(f"specialist_{cid}_")


# ── Test 6: control_only is recorded when dispatch returns empty ───────────


def test_control_only_recorded(tmp_path):
    proj = _make_project(tmp_path)
    fake_dispatch = SimpleNamespace(returncode=0, text="")

    with patch("ztare.worldmodel.residual_specialists.dispatch_model", return_value=fake_dispatch):
        with patch("ztare.worldmodel.residual_specialists._gate_candidates", return_value=[]):
            result = run_specialists(proj, dry_run=False)

    dispatches = result.get("dispatches", [])
    assert all(d.get("control_only") for d in dispatches), "all shards should be control_only on empty response"


# ── Test 7: receipt schema ─────────────────────────────────────────────────


def test_receipt_schema(tmp_path):
    proj = _make_project(tmp_path)
    fake_dispatch = SimpleNamespace(returncode=0, text="")

    with patch("ztare.worldmodel.residual_specialists.dispatch_model", return_value=fake_dispatch):
        with patch("ztare.worldmodel.residual_specialists._gate_candidates", return_value=[]):
            result = run_specialists(proj, dry_run=False)

    assert result["_schema"] == RECEIPT_SCHEMA
    assert "shards" in result
    assert "dispatches" in result
    assert "selection" in result
    assert "partition_too_fine" in result
    assert "unification_attempted" in result
    assert "sharding_mode" in result

    # check jsonl was written
    receipt_file = proj / "workspace" / "residual_specialists.jsonl"
    assert receipt_file.exists()
    rows = [json.loads(l) for l in receipt_file.read_text().splitlines() if l.strip()]
    assert rows[-1]["_schema"] == RECEIPT_SCHEMA


# ── Test 8: MDL tie-break ─────────────────────────────────────────────────


def test_mdl_tiebreak(tmp_path):
    # shorter code → smaller MDL
    f1 = tmp_path / "a.py"
    f2 = tmp_path / "b.py"
    f1.write_text("def solve(g): return g\n", encoding="utf-8")
    f2.write_text("\n".join(["def solve(g):"] + [f"    x{i} = {i}" for i in range(50)] + ["    return g"]),
                  encoding="utf-8")
    assert description_units(f1.read_text()) < description_units(f2.read_text())


# ── Test 9: partition_too_fine on shared t==128 guard ─────────────────────


def test_partition_too_fine_shared_guard(tmp_path):
    f1 = tmp_path / "patch_a.py"
    f2 = tmp_path / "patch_b.py"
    # both patches guard on t == 128
    code = "def solve(g):\n    if t == 128:\n        return g\n    return g\n"
    f1.write_text(code, encoding="utf-8")
    f2.write_text(code, encoding="utf-8")

    shard_patches = [
        {"class_id": "a", "candidate_path": str(f1)},
        {"class_id": "b", "candidate_path": str(f2)},
    ]
    assert _partition_too_fine(shard_patches) is True


# ── Test 10: partition_too_fine suppresses composition ────────────────────


def test_partition_too_fine_suppresses_composition(tmp_path):
    proj = _make_project(tmp_path)
    fake_dispatch = SimpleNamespace(returncode=0, text="")

    with patch("ztare.worldmodel.residual_specialists.dispatch_model", return_value=fake_dispatch):
        with patch("ztare.worldmodel.residual_specialists._gate_candidates", return_value=[]):
            with patch("ztare.worldmodel.residual_specialists._partition_too_fine", return_value=True):
                result = run_specialists(proj, dry_run=False)

    assert result["partition_too_fine"] is True
    assert result["composition_deferred"] is True
    # unification not attempted when partition_too_fine
    assert result["unification_attempted"] is False


# ── Test 11: unification bookkeeping present ──────────────────────────────


def test_unification_bookkeeping(tmp_path):
    proj = _make_project(tmp_path)
    shards = build_shards(proj, max_shards=4)

    fake_code = "def solve(grid): return grid\n"
    fake_payload = json.dumps({
        "test_model_py": fake_code,
        "thesis_markdown": "MECHANISM: timer over-fires\nDISCRIMINATOR: check t==5 band",
        "control_receipts": {},
    })
    call_count = [0]

    def fake_dispatch(prompt, *, capability="agent", **kwargs):
        call_count[0] += 1
        return SimpleNamespace(returncode=0, text=fake_payload)

    def fake_gate(project_dir, paths, episodes=("visible", "holdout")):
        return [
            {"candidate": p, "visible_exact": 1, "visible_total": 1,
             "holdout_depth": 0, "holdout_total": 1,
             "load_error": None, "grid_dsl_expressible": True, "grid_dsl_size": 5}
            for p in paths
        ]

    with patch("ztare.worldmodel.residual_specialists.dispatch_model", side_effect=fake_dispatch):
        with patch("ztare.worldmodel.residual_specialists._gate_candidates", side_effect=fake_gate):
            result = run_specialists(proj, dry_run=False)

    # unification should have been attempted (>=2 productive shards)
    assert "unification" in result
    assert "attempted" in result["unification"]


# ── Test 12: investigated is recorded ────────────────────────────────────


def test_investigated_recorded(tmp_path):
    proj = _make_project(tmp_path, records=[_make_record(0, 0, t=1, claim_class="X")])
    inv_payload = json.dumps({
        "test_model_py": "INVESTIGATED",
        "thesis_markdown": "already covered by prior patch",
        "control_receipts": {},
    })
    fake_dispatch = SimpleNamespace(returncode=0, text=inv_payload)

    with patch("ztare.worldmodel.residual_specialists.dispatch_model", return_value=fake_dispatch):
        with patch("ztare.worldmodel.residual_specialists._gate_candidates", return_value=[]):
            result = run_specialists(proj, dry_run=False)

    dispatches = result["dispatches"]
    assert any(d.get("investigated") for d in dispatches)


# ── Test 13: build_frontier reads champion from candidate_memory ──────────


def test_build_frontier_champion_record(tmp_path):
    proj = _make_project_with_champion(tmp_path)
    frontier = build_frontier(proj)

    assert frontier["champion_ref"] == "abc12345"
    assert frontier["survives_to_step"] == 3
    ff = frontier["first_failure"]
    assert ff is not None
    assert ff["t"] == 7
    assert ff["action"] == 1
    assert ff["step_index"] == 2
    cells = ff["divergent_cells"]
    assert len(cells) == 1
    assert cells[0]["row"] == 5 and cells[0]["col"] == 5


# ── Test 14: eliminated families rendered in briefing ────────────────────


def test_eliminated_families_in_briefing(tmp_path):
    proj = _make_project_with_champion(tmp_path)
    ws = proj / "workspace"

    # Plant an investigated nogood
    ng_row = {
        "schema": "spec_visible_nogood_v1",
        "eliminated_hypothesis": "timer-band under-clear hypothesis",
        "provenance": {"source": "investigated_science_turn"},
    }
    (ws / "spec_visible_nogoods.jsonl").write_text(json.dumps(ng_row) + "\n", encoding="utf-8")

    frontier = build_frontier(proj)
    assert "timer-band under-clear hypothesis" in frontier["eliminated_families"]

    shards = build_shards(proj, max_shards=2)
    briefing = specialist_briefing(shards[0], proj)
    assert "timer-band under-clear hypothesis" in briefing
    assert "ELIMINATED FAMILIES" in briefing


# ── Test 15: MECHANISM:/DISCRIMINATOR: parsed from thesis ────────────────


def test_parse_mechanism_discriminator():
    thesis = "Some preamble.\nMECHANISM: timer over-fires at band boundary\nDISCRIMINATOR: observe t==19 with action=0\nEnd."
    assert _parse_mechanism(thesis) == "timer over-fires at band boundary"
    assert _parse_discriminator(thesis) == "observe t==19 with action=0"


def test_parse_mechanism_missing():
    assert _parse_mechanism("") is None
    assert _parse_discriminator("no mechanism here") is None


# ── Test 16: mechanism+discriminator recorded in dispatch entry ────────────


def test_mechanism_recorded_in_dispatch(tmp_path):
    proj = _make_project(tmp_path)
    thesis = "MECHANISM: champion under-clears the timer band\nDISCRIMINATOR: t==19 a=0 cell (61,14)"
    fake_payload = json.dumps({
        "test_model_py": "def solve(grid): return grid\n",
        "thesis_markdown": thesis,
        "control_receipts": {},
    })
    fake_dispatch = SimpleNamespace(returncode=0, text=fake_payload)

    with patch("ztare.worldmodel.residual_specialists.dispatch_model", return_value=fake_dispatch):
        with patch("ztare.worldmodel.residual_specialists._gate_candidates", return_value=[]):
            result = run_specialists(proj, dry_run=False)

    dispatches = result["dispatches"]
    assert any(d.get("mechanism") == "champion under-clears the timer band" for d in dispatches)
    assert any(d.get("discriminator") == "t==19 a=0 cell (61,14)" for d in dispatches)


# ── Test 17: refuted-mechanism bookkeeping row appended ──────────────────


def test_refuted_mechanism_bookkeeping(tmp_path):
    proj = _make_project(tmp_path)
    ws = proj / "workspace"

    # Bug-2: genuine refutation = candidate loaded, no load_error, just performed worse
    _append_refuted_mechanism(proj, "timer over-fires hypothesis", {"visible_exact": 0, "holdout_depth": -1})
    ng_path = ws / "spec_visible_nogoods.jsonl"
    assert ng_path.exists()

    rows = [json.loads(l) for l in ng_path.read_text().splitlines() if l.strip()]
    assert len(rows) == 1
    row = rows[0]
    assert row["eliminated_hypothesis"] == "timer over-fires hypothesis"
    assert row["provenance"]["source"] == "gate_refuted_candidate"
    # NOT investigated_science_turn — so build_frontier doesn't credit it
    frontier = build_frontier(proj)
    assert "timer over-fires hypothesis" not in frontier["eliminated_families"]


# ── Test 18: --by-cells legacy path still works ───────────────────────────


def test_by_cells_legacy_path(tmp_path):
    proj = _make_project(tmp_path)
    shards = build_shards(proj, max_shards=4, by_cells=True)
    # Two distinct cell classes → 2 shards
    assert len(shards) == 2
    # Legacy shards have no mechanism_family
    for s in shards:
        assert s.get("mechanism_family") is None


def test_by_cells_dry_run(tmp_path, monkeypatch):
    # Force env override so allocate_width is bypassed; old default was 4
    monkeypatch.setenv("ZTARE_SPECIALIST_MAX_SHARDS", "4")
    proj = _make_project(tmp_path)
    with patch("ztare.worldmodel.residual_specialists.dispatch_model") as mock_dispatch:
        result = run_specialists(proj, dry_run=True, by_cells=True)
    mock_dispatch.assert_not_called()
    assert result["dry_run"] is True
    # sharding_mode not in dry-run dict; shards present
    assert len(result["shards"]) == 2


# ── Test 19: Bug-1 — full selection path marks candidate as selected ──────
# Regression: maiden run "no candidate produced" due to relative vs absolute
# path mismatch in gate_by_path lookup.


def test_selection_marks_gated_when_candidate_exists(tmp_path):
    """run_specialists must mark a dispatch selected=True when gate returns a valid row."""
    proj = _make_project(tmp_path)
    shards = build_shards(proj, max_shards=1)
    cid = shards[0]["class_id"]

    fake_code = "def solve(grid): return grid\n"
    fake_payload = json.dumps({
        "test_model_py": fake_code,
        "thesis_markdown": "MECHANISM: test-mech\nDISCRIMINATOR: test-disc",
        "control_receipts": {},
    })
    fake_dispatch = SimpleNamespace(returncode=0, text=fake_payload)

    # gate returns absolute path keyed by "candidate" — simulating real batch_gate
    def fake_gate(project_dir, paths, episodes=("visible", "holdout")):
        # paths are absolute after bug-1 fix; return rows with matching absolute key
        return [
            {
                "candidate": p,   # must match candidate_path exactly
                "visible_exact": 5,
                "visible_total": 10,
                "holdout_depth": 2,
                "holdout_total": 4,
                "load_error": None,
                "grid_dsl_expressible": True,
                "grid_dsl_size": 20,
            }
            for p in paths
        ]

    with patch("ztare.worldmodel.residual_specialists.dispatch_model", return_value=fake_dispatch):
        with patch("ztare.worldmodel.residual_specialists._gate_candidates", side_effect=fake_gate):
            result = run_specialists(proj, dry_run=False)

    sel = result["selection"]
    assert len(sel) >= 1
    selected = [s for s in sel if s.get("selected")]
    assert len(selected) >= 1, f"expected >=1 selected; got selection={sel}"
    assert selected[0]["reason"] == "gated"
    assert selected[0].get("gate_summary") is not None


# ── Test 20: Bug-2 — form errors go to form_error receipt, not mechanism ledger


def test_form_error_not_refuted_mechanism(tmp_path):
    """load_error from gate must produce form_error receipt, never mechanism refutation."""
    proj = _make_project(tmp_path)
    ws = proj / "workspace"

    # Simulate a form-error gate receipt
    sr = {"class_id": "mech_lane_a", "candidate_path": str(tmp_path / "bad.py"), "mechanism": "bad-mech"}
    gr = {"load_error": "PATCH_BASE sha256 must be the full 64-hex digest.", "visible_exact": -1}
    _append_form_error_receipt(proj, sr, gr)

    ng_path = ws / "spec_visible_nogoods.jsonl"
    assert ng_path.exists()
    rows = [json.loads(l) for l in ng_path.read_text().splitlines() if l.strip()]
    assert len(rows) == 1
    row = rows[0]
    # Must be form_error kind and source, NOT gate_refuted_candidate
    assert row["kind"] == "form_error"
    assert row["provenance"]["source"] == "form_error"
    assert "eliminated_hypothesis" not in row, "form errors must not set eliminated_hypothesis"
    # build_frontier must NOT pick this up as an eliminated family
    frontier = build_frontier(proj)
    assert not frontier["eliminated_families"]


# ── Test 21: Bug-3 — sha normalization expands truncated PATCH_BASE sha ──


def test_normalize_patch_base_sha_expands_prefix(tmp_path):
    """_normalize_patch_base_sha must expand a 16-hex prefix to the full 64-hex."""
    full_sha = "e2e9ad0c8271a9d0a6f7e8fd192f07a2c73f5a7403679dedb8e2b2a70888761c"
    short_sha = full_sha[:16]  # e2e9ad0c8271a9d0

    code = f'PATCH_BASE = {{"source_ref": "workspace/submissions/iter_001.py", "sha256": "{short_sha}"}}\n\ndef solve(g): return g\n'
    notes: list[str] = []
    result = _normalize_patch_base_sha(code, full_sha, notes)

    assert full_sha in result, "full sha must appear in normalized code"
    # The short sha appears as a substring of the full sha (it's a prefix) — that's fine.
    # What must NOT appear is the short sha as a standalone value (surrounded by quotes).
    assert f'"{short_sha}"' not in result, "truncated sha must not appear as standalone quoted value"
    assert len(notes) == 1 and "patch_base_sha_expanded" in notes[0]


def test_normalize_patch_base_sha_noop_on_full(tmp_path):
    """_normalize_patch_base_sha must not modify code that already has the full sha."""
    full_sha = "e2e9ad0c8271a9d0a6f7e8fd192f07a2c73f5a7403679dedb8e2b2a70888761c"
    code = f'PATCH_BASE = {{"sha256": "{full_sha}"}}\n'
    notes: list[str] = []
    result = _normalize_patch_base_sha(code, full_sha, notes)
    assert result == code
    assert not notes


def test_patch_base_directive_renders_full_sha(tmp_path):
    """_patch_base_directive must render the sha on its own line for verbatim copy."""
    proj = _make_project_with_champion(tmp_path)
    directive = _patch_base_directive(proj)
    # Must have the sha on its own line with the verbatim-copy label
    assert "sha256 (copy verbatim, all 64 hex):" in directive
    # Must not embed sha inline in the PATCH_BASE: line itself (old format)
    first_line = directive.splitlines()[0]
    assert "sha256=" not in first_line


# ── Test 22: _specialist_mode reads env var ───────────────────────────────


def test_specialist_mode_default(monkeypatch):
    monkeypatch.delenv("ZTARE_SPECIALIST_MODE", raising=False)
    assert _specialist_mode() == "workbench"


def test_specialist_mode_sealed(monkeypatch):
    monkeypatch.setenv("ZTARE_SPECIALIST_MODE", "sealed")
    assert _specialist_mode() == "sealed"


def test_specialist_mode_workbench_explicit(monkeypatch):
    monkeypatch.setenv("ZTARE_SPECIALIST_MODE", "workbench")
    assert _specialist_mode() == "workbench"


def test_specialist_mode_unknown_defaults_to_workbench(monkeypatch):
    monkeypatch.setenv("ZTARE_SPECIALIST_MODE", "garbage")
    assert _specialist_mode() == "workbench"


# ── Test 23: workbench briefing contains preflight paragraph ─────────────


def test_workbench_briefing_has_preflight_paragraph(tmp_path, monkeypatch):
    monkeypatch.setenv("ZTARE_SPECIALIST_MODE", "workbench")
    proj = _make_project(tmp_path)
    shards = build_shards(proj, max_shards=1)
    briefing = specialist_briefing(shards[0], proj, mode="workbench")
    assert "Workbench" in briefing
    assert "PREFLIGHT.md" in briefing
    assert "preflight command BEFORE submitting" in briefing


def test_sealed_briefing_has_no_preflight_paragraph(tmp_path):
    proj = _make_project(tmp_path)
    shards = build_shards(proj, max_shards=1)
    briefing = specialist_briefing(shards[0], proj, mode="sealed")
    assert "PREFLIGHT.md" not in briefing


# ── Test 24: _stage_specialist_pack structure ─────────────────────────────


def _make_project_with_episodes(tmp_path: Path) -> Path:
    """Project with champion + two episode files."""
    proj = tmp_path / "projects" / "synth_proj"
    ws = proj / "workspace"
    ws.mkdir(parents=True)
    ep_dir = proj / "raw" / "episodes"
    ep_dir.mkdir(parents=True)
    # Minimal JSONL episode rows
    row = json.dumps({"s": [[0]], "a": 0, "t": 0, "s_next": [[1]]})
    (ep_dir / "episode_001.jsonl").write_text(row + "\n", encoding="utf-8")
    (ep_dir / "episode_002.jsonl").write_text(row + "\n", encoding="utf-8")
    (proj / "test_model.py").write_text("# champion\ndef solve(g): return g\n", encoding="utf-8")
    (ws / "candidate_memory.json").write_text(json.dumps({"records": []}), encoding="utf-8")
    return proj


def test_stage_specialist_pack_creates_required_files(tmp_path, monkeypatch):
    """Pack dir must contain BRIEFING.md, PREFLIGHT.md, test_model.py, episode files."""
    # Point workbench root inside tmp_path so we don't pollute $TMPDIR
    wb_root = tmp_path / "wb"
    monkeypatch.setattr(
        "ztare.worldmodel.residual_specialists.tempfile.gettempdir",
        lambda: str(wb_root),
    )
    proj = _make_project_with_episodes(tmp_path)
    briefing = "test briefing content"
    pack_dir = _stage_specialist_pack(proj, briefing, "cls_x", survives_to_step=3)

    assert (pack_dir / "BRIEFING.md").exists()
    assert (pack_dir / "PREFLIGHT.md").read_text().count("batch_gate") >= 1
    assert (pack_dir / "test_model.py").exists()
    assert (pack_dir / "MANIFEST.json").exists()
    # episodes staged
    ep_files = list((pack_dir / "raw" / "episodes").glob("*.jsonl"))
    assert len(ep_files) == 2
    # rubric placed at parents[1]/rubrics/<name>.json
    rubric_path = pack_dir.parents[1] / "rubrics" / f"{proj.name}.json"
    assert rubric_path.exists()


def test_stage_specialist_pack_preflight_contains_survives(tmp_path, monkeypatch):
    wb_root = tmp_path / "wb"
    monkeypatch.setattr(
        "ztare.worldmodel.residual_specialists.tempfile.gettempdir",
        lambda: str(wb_root),
    )
    proj = _make_project_with_episodes(tmp_path)
    pack_dir = _stage_specialist_pack(proj, "briefing", "cls_x", survives_to_step=7)
    preflight = (pack_dir / "PREFLIGHT.md").read_text()
    assert "7" in preflight


# ── Test 25: batch_gate runs against staged pack (rubric resolvable) ──────


def test_batch_gate_against_staged_pack(tmp_path, monkeypatch):
    """batch_gate must return sane counts when run against the staged pack."""
    import sys
    wb_root = tmp_path / "wb"
    monkeypatch.setattr(
        "ztare.worldmodel.residual_specialists.tempfile.gettempdir",
        lambda: str(wb_root),
    )
    proj = _make_project_with_episodes(tmp_path)
    pack_dir = _stage_specialist_pack(proj, "briefing", "cls_y", survives_to_step=1)

    # Candidate: trivial pass-through (identity)
    candidate = tmp_path / "cand.py"
    candidate.write_text(
        "def step(grid, action, t): return grid\n",
        encoding="utf-8",
    )

    from ztare.worldmodel.batch_gate import batch_gate
    results = batch_gate(str(pack_dir), [str(candidate)], episodes=("visible",))
    assert len(results) == 1
    rec = results[0]
    assert "load_error" not in rec or rec["load_error"] is None, f"load_error: {rec.get('load_error')}"
    assert rec["visible_total"] >= 0
    assert rec["visible_exact"] >= 0


# ── Test 26: dispatch dispatch records mode + preflight_receipts ──────────


def test_dispatch_records_mode_workbench(tmp_path, monkeypatch):
    """run_specialists receipt must record mode=workbench and preflight_receipts."""
    monkeypatch.setenv("ZTARE_SPECIALIST_MODE", "workbench")
    monkeypatch.setenv("ZTARE_SPECIALIST_MAX_SHARDS", "1")
    proj = _make_project(tmp_path)

    fake_payload = json.dumps({
        "test_model_py": "def solve(g): return g\n",
        "thesis_markdown": "MECHANISM: test\nDISCRIMINATOR: none",
        "control_receipts": {},
    })

    def fake_dispatch(prompt, *, capability="agent", **kwargs):
        return SimpleNamespace(returncode=0, text=fake_payload)

    def fake_gate(project_dir, paths, episodes=("visible", "holdout")):
        return [
            {"candidate": p, "visible_exact": 1, "visible_total": 1,
             "holdout_depth": 0, "holdout_total": 1,
             "load_error": None, "grid_dsl_expressible": True, "grid_dsl_size": 5}
            for p in paths
        ]

    # Also stub _stage_specialist_pack so it doesn't touch real $TMPDIR
    wb_root = tmp_path / "wb"
    monkeypatch.setattr(
        "ztare.worldmodel.residual_specialists.tempfile.gettempdir",
        lambda: str(wb_root),
    )

    with patch("ztare.worldmodel.residual_specialists.dispatch_model", side_effect=fake_dispatch):
        with patch("ztare.worldmodel.residual_specialists._gate_candidates", side_effect=fake_gate):
            result = run_specialists(proj, dry_run=False)

    dispatches = result["dispatches"]
    assert len(dispatches) >= 1
    for d in dispatches:
        assert d.get("mode") == "workbench", f"expected mode=workbench, got {d.get('mode')}"
        assert "preflight_receipts" in d


def test_dispatch_records_mode_sealed(tmp_path, monkeypatch):
    """When ZTARE_SPECIALIST_MODE=sealed, dispatch rows record mode=sealed."""
    monkeypatch.setenv("ZTARE_SPECIALIST_MODE", "sealed")
    monkeypatch.setenv("ZTARE_SPECIALIST_MAX_SHARDS", "1")
    proj = _make_project(tmp_path)

    fake_dispatch = SimpleNamespace(returncode=0, text="")

    with patch("ztare.worldmodel.residual_specialists.dispatch_model", return_value=fake_dispatch):
        with patch("ztare.worldmodel.residual_specialists._gate_candidates", return_value=[]):
            result = run_specialists(proj, dry_run=False)

    for d in result["dispatches"]:
        assert d.get("mode") == "sealed"
        assert d.get("preflight_receipts") == -1


def test_routine_claim_lint():
    """CDC-prompt transplant: hand-waved compatibility claims are surfaced
    in receipts (observable lint, never a strike)."""
    from ztare.worldmodel.residual_specialists import _routine_claim_lint

    flagged = _routine_claim_lint(
        "MECHANISM: the slab commutes left.\n"
        "The compatibility of the two phases is routine and the gluing is clearly fine."
    )
    assert len(flagged) == 2
    assert all(f.startswith("routine_claim:") for f in flagged)
    assert _routine_claim_lint("MECHANISM: x. Witness: transition t=19 shows the gluing.") == []
    assert _routine_claim_lint("") == []


def test_briefing_carries_idea_not_wording_clause(tmp_path):
    from ztare.worldmodel.residual_specialists import build_shards, specialist_briefing
    proj = _make_project(tmp_path)
    b = specialist_briefing(build_shards(proj, max_shards=1)[0], proj)
    assert "mathematical idea it uses, not its wording" in b
    assert "will not survive audit" in b
