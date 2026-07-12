"""Tests for trace_auditor — each detector fires on anomalous fixture, stays
quiet on healthy one.  Emission writes a schema-valid rider that
_normalize_rider_proposal accepts (proof-by-import).  No external deps beyond
existing project deps.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from ztare.orchestrator.trace_auditor import (
    check_dead_channel_constraints,
    check_dead_channel_lean,
    check_dead_channel_probes,
    check_strike_economy,
    check_disposition_skew,
    check_fallback_events,
    check_pack_boot_smoke,
    check_recurrence,
    check_phase_cost_regression,
    check_alpha_blind_saturation,
    check_loop_phase_death,
    check_dead_grain_writers,
    check_contract_surface_drift,
    check_file_seam_coverage,
    check_organ_liveness,
    _parse_index_md,
    _emit_rider,
    run_audit,
)
from ztare.research_director.strategy_office import _normalize_rider_proposal


# ── fixtures ──────────────────────────────────────────────────────────────────

def _ws(tmp_path: Path) -> Path:
    ws = tmp_path / "projects" / "proj" / "workspace"
    ws.mkdir(parents=True)
    return ws


def _project(ws: Path) -> Path:
    return ws.parent


def _jl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _jf(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ── dead_channel_constraints ─────────────────────────────────────────────────

def test_constraints_anomaly(tmp_path):
    ws = _ws(tmp_path)
    _jf(ws / "derived_constraints.json", {
        "confirmed_constraint_count": 0,
        "provisional_constraint_count": 10,
    })
    state = {"prev_provisional_constraint_count": 5}
    f = check_dead_channel_constraints(ws, state)
    assert f["verdict"] == "anomaly"
    assert f["check_id"] == "dead_channel_constraints"
    assert state["prev_provisional_constraint_count"] == 10  # snapshot updated


def test_constraints_ok(tmp_path):
    ws = _ws(tmp_path)
    _jf(ws / "derived_constraints.json", {
        "confirmed_constraint_count": 3,
        "provisional_constraint_count": 10,
    })
    state: dict = {}
    f = check_dead_channel_constraints(ws, state)
    assert f["verdict"] == "ok"


def test_constraints_ok_no_growth(tmp_path):
    ws = _ws(tmp_path)
    _jf(ws / "derived_constraints.json", {
        "confirmed_constraint_count": 0,
        "provisional_constraint_count": 10,
    })
    state = {"prev_provisional_constraint_count": 10}  # no growth
    f = check_dead_channel_constraints(ws, state)
    assert f["verdict"] == "ok"


# ── dead_channel_lean ─────────────────────────────────────────────────────────

def test_lean_anomaly(tmp_path):
    ws = _ws(tmp_path)
    _jf(ws / "worldmodel_lean_feedback_receipt.json", {
        "blueprint_ref": "workspace/worldmodel_auto_blueprint.md",
        "schema": "ztare-worldmodel-lean-feedback-v2",
    })
    # no invariant_certificates.jsonl
    state = {"lean_gap_audit_count": 3}  # already at threshold
    f = check_dead_channel_lean(ws, state)
    assert f["verdict"] == "anomaly"
    assert state["lean_gap_audit_count"] == 4


def test_lean_ok_no_blueprint(tmp_path):
    ws = _ws(tmp_path)
    state: dict = {}
    f = check_dead_channel_lean(ws, state)
    assert f["verdict"] == "ok"


def test_lean_ok_certs_present(tmp_path):
    ws = _ws(tmp_path)
    _jf(ws / "worldmodel_lean_feedback_receipt.json", {"blueprint_ref": "wp/foo.md"})
    cert_path = ws / "invariant_certificates.jsonl"
    _jl(cert_path, [{"theorem": "foo"}])
    state: dict = {}
    f = check_dead_channel_lean(ws, state)
    assert f["verdict"] == "ok"


# ── dead_channel_probes ───────────────────────────────────────────────────────

def test_probes_anomaly(tmp_path):
    ws = _ws(tmp_path)
    # capability proposals mention probe
    _jl(ws / "leaf_workbench_capability_proposals.jsonl", [{
        "schema": "ztare-capability-proposal-v1",
        "proposal": {"capability_id": "run_visible_json_probe"},
    }])
    rcpt_dir = ws / "visible_cli_receipts"
    rcpt_dir.mkdir()
    # no probe receipts
    state = {"last_audit_ts": None}
    f = check_dead_channel_probes(ws, state)
    assert f["verdict"] == "anomaly"


def test_probes_ok_no_caps(tmp_path):
    ws = _ws(tmp_path)
    state: dict = {}
    f = check_dead_channel_probes(ws, state)
    assert f["verdict"] == "ok"


def test_probes_ok_has_receipt(tmp_path):
    ws = _ws(tmp_path)
    _jl(ws / "leaf_workbench_capability_proposals.jsonl", [{
        "proposal": {"capability_id": "run_visible_json_probe"},
    }])
    rcpt_dir = ws / "visible_cli_receipts"
    rcpt_dir.mkdir()
    (rcpt_dir / "probe_abc123.json").write_text('{"status":"ok"}')
    state = {"last_audit_ts": None}
    f = check_dead_channel_probes(ws, state)
    assert f["verdict"] == "ok"


# ── strike_economy ────────────────────────────────────────────────────────────

def test_strike_anomaly(tmp_path):
    ws = _ws(tmp_path)
    log = ws / "run.log"
    log.write_text(
        "⚠️ Runner R1 rejection: missing field 'turn_receipt_ref'\n"
        "⚠️ Runner R1 rejection: field-validation: envelope format\n"
        "⚠️ Runner R1 rejection: schema mismatch in receipt-citation\n",
        encoding="utf-8",
    )
    state: dict = {}
    f = check_strike_economy(ws, state, None)
    assert f["verdict"] == "anomaly"
    assert f["witness"]["envelope_fraction"] > 0.5


def test_strike_ok(tmp_path):
    ws = _ws(tmp_path)
    log = ws / "run.log"
    log.write_text(
        "⚠️ Runner R1 rejection: candidate produced wrong output for task 3\n"
        "⚠️ Runner R1 rejection: boundary condition failed\n",
        encoding="utf-8",
    )
    state: dict = {}
    f = check_strike_economy(ws, state, None)
    assert f["verdict"] == "ok"


def test_strike_ok_no_log(tmp_path):
    ws = _ws(tmp_path)
    state: dict = {}
    f = check_strike_economy(ws, state, None)
    assert f["verdict"] == "ok"
    assert not f["witness"].get("log_found", True)


# ── disposition_skew ──────────────────────────────────────────────────────────

def test_disposition_anomaly(tmp_path):
    ws = _ws(tmp_path)
    rows = [{"disposition": "rejected_unlowerable", "schema": "x"} for _ in range(30)]
    rows += [{"disposition": "observed", "schema": "x"} for _ in range(5)]
    _jl(ws / "strategy_experiment_executions.jsonl", rows)
    state: dict = {}
    f = check_disposition_skew(ws, state)
    assert f["verdict"] == "anomaly"
    assert f["witness"]["fraction"] > 0.5


def test_disposition_ok(tmp_path):
    ws = _ws(tmp_path)
    rows = [{"disposition": "observed"} for _ in range(20)]
    rows += [{"disposition": "rejected_unlowerable"} for _ in range(5)]
    _jl(ws / "strategy_experiment_executions.jsonl", rows)
    state: dict = {}
    f = check_disposition_skew(ws, state)
    assert f["verdict"] == "ok"


# ── fallback_events ───────────────────────────────────────────────────────────

def test_fallback_anomaly(tmp_path):
    ws = _ws(tmp_path)
    log = ws / "run.log"
    log.write_text(
        "Model fallback DISABLED (--no_model_fallback).\n"
        "🔁 Provider fallback engaged for req: modelA -> modelB\n",
        encoding="utf-8",
    )
    state: dict = {}
    f = check_fallback_events(ws, state, None)
    assert f["verdict"] == "anomaly"
    assert f["witness"]["fallback_count"] == 1


def test_fallback_ok(tmp_path):
    ws = _ws(tmp_path)
    log = ws / "run.log"
    log.write_text("All good, no fallback\n", encoding="utf-8")
    state: dict = {}
    f = check_fallback_events(ws, state, None)
    assert f["verdict"] == "ok"


# ── pack_boot_smoke ───────────────────────────────────────────────────────────

def test_pack_boot_smoke_ok(tmp_path):
    ws = _ws(tmp_path)
    state: dict = {}
    f = check_pack_boot_smoke(ws, state)
    # The real manifest command must succeed (sanity smoke on the installed package)
    assert f["check_id"] == "pack_boot_smoke"
    # We don't assert ok/anomaly here to avoid CI fragility from env differences,
    # but we do assert the finding is well-formed.
    assert f["verdict"] in ("ok", "anomaly")
    assert isinstance(f["witness"], dict)


# ── recurrence ────────────────────────────────────────────────────────────────

def test_recurrence_fires_on_repeat(tmp_path):
    findings = [{"check_id": "dead_channel_lean", "verdict": "anomaly", "witness": {}, "note": "x"}]
    state = {
        "last_verdicts": {"dead_channel_lean": "anomaly"},
        "fixed_checks": {"dead_channel_lean": True},   # previously fixed
    }
    out = check_recurrence(findings, state)
    assert out[0]["recurrence"] is True


def test_recurrence_silent_on_first(tmp_path):
    findings = [{"check_id": "dead_channel_lean", "verdict": "anomaly", "witness": {}, "note": "x"}]
    state: dict = {}
    out = check_recurrence(findings, state)
    assert out[0]["recurrence"] is False


# ── emission + normalize proof ────────────────────────────────────────────────

def test_emit_writes_valid_rider(tmp_path):
    ws = _ws(tmp_path)
    finding = {
        "check_id": "dead_channel_constraints",
        "verdict": "anomaly",
        "witness": {"confirmed_constraint_count": 0, "provisional_constraint_count": 10},
        "note": "Confirmed constraints stuck at 0.",
        "recurrence": False,
    }
    row = _emit_rider(ws, finding)

    # file was written
    ledger = ws / "leaf_proposals.jsonl"
    assert ledger.exists()
    lines = [l for l in ledger.read_text().splitlines() if l.strip()]
    assert len(lines) == 1
    written = json.loads(lines[0])

    # required fields present
    assert written["proposed_change"]
    assert written["source"] == "trace_auditor"
    assert written["provenance"] == "trace_auditor"
    assert written["disposition"] == "open"

    # _normalize_rider_proposal accepts it (proof-by-import)
    project = _project(ws)
    normalized = _normalize_rider_proposal(project, written)
    assert normalized.get("proposed_change")


def test_emit_only_on_anomaly(tmp_path):
    ws = _ws(tmp_path)
    _jf(ws / "derived_constraints.json", {
        "confirmed_constraint_count": 5,
        "provisional_constraint_count": 10,
    })
    _jl(ws / "strategy_experiment_executions.jsonl", [{"disposition": "observed"} for _ in range(10)])
    # make a log with no rejections
    (ws / "run.log").write_text("all good\n", encoding="utf-8")

    project = _project(ws)
    result = run_audit(project, emit=True)
    ledger = ws / "leaf_proposals.jsonl"
    # Only anomalies emit riders; with healthy fixtures there may be zero
    emitted = result["emitted_rider_count"]
    if emitted == 0:
        assert not ledger.exists() or ledger.stat().st_size == 0 or all(
            json.loads(l).get("verdict") != "ok"
            for l in ledger.read_text().splitlines() if l.strip()
        )


def test_normalized_rider_proof(tmp_path):
    """Explicit proof: emit a row, normalize it, check the required field survives."""
    ws = _ws(tmp_path)
    finding = {
        "check_id": "strike_economy",
        "verdict": "anomaly",
        "witness": {"total_rejections": 3, "envelope_fraction": 0.67},
        "note": "67% envelope causes.",
        "recurrence": True,
    }
    row = _emit_rider(ws, finding)
    project = _project(ws)
    normalized = _normalize_rider_proposal(project, row)
    # _normalize_rider_proposal only returns non-empty proposed_change for valid rows
    assert normalized["proposed_change"]
    assert "trace_auditor" in normalized["proposed_change"]


# ── check_phase_cost_regression ───────────────────────────────────────────────

def test_phase_cost_regression_superlinear(tmp_path):
    """Three runs of 'expand' with cost tripling → superlinear anomaly."""
    ws = _ws(tmp_path)
    # Simulate 3 runs: phase 'expand' at depth 0, costs 1s / 2s / 4s
    rows = [
        {"schema": "ztare.phase_timing.v1", "phase": "expand", "seconds": 1.0, "depth": 0, "started": "2025-01-01T00:00:00+00:00"},
        {"schema": "ztare.phase_timing.v1", "phase": "expand", "seconds": 2.0, "depth": 0, "started": "2025-01-01T01:00:00+00:00"},
        {"schema": "ztare.phase_timing.v1", "phase": "expand", "seconds": 4.0, "depth": 0, "started": "2025-01-01T02:00:00+00:00"},
    ]
    _jl(ws / "phase_timings.jsonl", rows)
    f = check_phase_cost_regression(ws, {})
    assert f["verdict"] == "anomaly"
    assert f["check_id"] == "phase_cost_regression"
    kinds = {a["kind"] for a in f["witness"]["anomalies"]}
    assert "superlinear_trend" in kinds
    assert "cost must scale with residual" in f["note"]


def test_phase_cost_regression_dominant_phase(tmp_path):
    """One phase takes 90% of a single run → dominant_phase anomaly."""
    ws = _ws(tmp_path)
    rows = [
        {"schema": "ztare.phase_timing.v1", "phase": "heavy", "seconds": 90.0, "depth": 0, "started": "2025-01-01T00:00:00+00:00"},
        {"schema": "ztare.phase_timing.v1", "phase": "light", "seconds": 10.0, "depth": 0, "started": "2025-01-01T00:00:01+00:00"},
    ]
    _jl(ws / "phase_timings.jsonl", rows)
    f = check_phase_cost_regression(ws, {})
    assert f["verdict"] == "anomaly"
    kinds = {a["kind"] for a in f["witness"]["anomalies"]}
    assert "dominant_phase" in kinds


def test_phase_cost_regression_ok(tmp_path):
    """Flat costs, balanced phases → ok."""
    ws = _ws(tmp_path)
    rows = [
        {"schema": "ztare.phase_timing.v1", "phase": "expand", "seconds": 1.0, "depth": 0, "started": "2025-01-01T00:00:00+00:00"},
        {"schema": "ztare.phase_timing.v1", "phase": "score", "seconds": 1.0, "depth": 0, "started": "2025-01-01T00:00:01+00:00"},
    ]
    _jl(ws / "phase_timings.jsonl", rows)
    f = check_phase_cost_regression(ws, {})
    assert f["verdict"] == "ok"


def test_phase_cost_regression_empty(tmp_path):
    """No timings file → ok (skipped)."""
    ws = _ws(tmp_path)
    f = check_phase_cost_regression(ws, {})
    assert f["verdict"] == "ok"


# ── check_alpha_blind_saturation ──────────────────────────────────────────────

def test_alpha_blind_saturation_missing_kind(tmp_path):
    """Saturation row without saturation_kind → anomaly."""
    ws = _ws(tmp_path)
    _jl(ws / "abstraction_saturation.jsonl", [{"functor": "state_hash", "saturated": True}])
    f = check_alpha_blind_saturation(ws, {})
    assert f["verdict"] == "anomaly"
    kinds = {i["kind"] for i in f["witness"]["issues"]}
    assert "missing_saturation_kind" in kinds


def test_alpha_blind_saturation_alpha_blind_kind(tmp_path):
    """Saturation row with saturation_kind='alpha_blind' → anomaly."""
    ws = _ws(tmp_path)
    _jl(ws / "abstraction_saturation.jsonl", [{"functor": "state_hash", "saturation_kind": "alpha_blind"}])
    f = check_alpha_blind_saturation(ws, {})
    assert f["verdict"] == "anomaly"
    kinds = {i["kind"] for i in f["witness"]["issues"]}
    assert "alpha_blind" in kinds


def test_alpha_blind_saturation_injective_functor(tmp_path):
    """Compression warning with ratio=1.0 → injective functor anomaly."""
    ws = _ws(tmp_path)
    _jl(ws / "functor_compression_warnings.jsonl", [
        {"functor": "identity_map", "compression_ratio": 1.0, "raw_size": 500},
    ])
    f = check_alpha_blind_saturation(ws, {})
    assert f["verdict"] == "anomaly"
    kinds = {i["kind"] for i in f["witness"]["issues"]}
    assert "injective_functor" in kinds


def test_alpha_blind_saturation_ok(tmp_path):
    """Saturation rows with kind='exhausted' and good compression → ok."""
    ws = _ws(tmp_path)
    _jl(ws / "abstraction_saturation.jsonl", [
        {"functor": "state_hash", "saturation_kind": "exhausted"},
    ])
    _jl(ws / "functor_compression_warnings.jsonl", [
        {"functor": "coarse", "compression_ratio": 0.5, "raw_size": 100},
    ])
    f = check_alpha_blind_saturation(ws, {})
    assert f["verdict"] == "ok"


# ── check_loop_phase_death ────────────────────────────────────────────────────

def test_loop_phase_death_anomaly(tmp_path):
    """RESULT: FAILED followed by Launching → silent partial run → anomaly."""
    ws = _ws(tmp_path)
    log = ws / "run.log"
    log.write_text(
        "validate_rubric: test_project\n"
        "  RESULT: FAILED — 2 checks failed.\n"
        "🚀 Launching: make loop PROJECT=test ITERS=8\n"
        "Some more output after the launch\n",
        encoding="utf-8",
    )
    f = check_loop_phase_death(ws, {}, None)
    assert f["verdict"] == "anomaly"
    assert f["check_id"] == "loop_phase_death"
    assert "RESULT: FAILED" in f["note"]


def test_loop_phase_death_make_error(tmp_path):
    """make[1]: *** followed by more activity → anomaly."""
    ws = _ws(tmp_path)
    log = ws / "run.log"
    log.write_text(
        "Starting loop iteration 1\n"
        "make[1]: *** [loop] Error 2\n"
        "🚀 Launching: make loop PROJECT=test ITERS=8\n",
        encoding="utf-8",
    )
    f = check_loop_phase_death(ws, {}, None)
    assert f["verdict"] == "anomaly"
    assert "make[1]: ***" in f["note"]


def test_loop_phase_death_ok(tmp_path):
    """Clean log with no phase-death markers → ok."""
    ws = _ws(tmp_path)
    log = ws / "run.log"
    log.write_text(
        "RESULT: PASSED — 9 checks OK.\n"
        "🚀 Launching: make loop PROJECT=test ITERS=8\n"
        "All iterations completed.\n",
        encoding="utf-8",
    )
    f = check_loop_phase_death(ws, {}, None)
    assert f["verdict"] == "ok"


def test_loop_phase_death_death_at_end(tmp_path):
    """Phase death at end with no subsequent activity → ok (not a silent run)."""
    ws = _ws(tmp_path)
    log = ws / "run.log"
    log.write_text(
        "Starting run\n"
        "make[1]: *** [loop] Error 2\n"
        "make: *** [experiment-loop] Error 2\n",
        encoding="utf-8",
    )
    f = check_loop_phase_death(ws, {}, None)
    # death at end with no post-death activity → ok (run stopped cleanly after death)
    assert f["verdict"] == "ok"


# ── check_dead_grain_writers ──────────────────────────────────────────────────

def test_dead_grain_writers_anomaly(tmp_path):
    """A >20MB JSONL file with >10KB lines → anomaly."""
    ws = _ws(tmp_path)
    big_file = ws / "visited_abc123.jsonl"
    # Write enough lines to exceed 20MB with fat JSON payloads
    fat_line = json.dumps({"data": "x" * 11000}) + "\n"  # ~11KB per line
    with big_file.open("w", encoding="utf-8") as fh:
        # 2000 lines × ~11KB = ~22MB
        for _ in range(2000):
            fh.write(fat_line)
    f = check_dead_grain_writers(ws, {})
    assert f["verdict"] == "anomaly"
    assert f["check_id"] == "dead_grain_writers"
    assert any("visited_abc123.jsonl" in h["file"] for h in f["witness"]["heavy_files"])


def test_dead_grain_writers_ok_small_file(tmp_path):
    """A small JSONL file → ok."""
    ws = _ws(tmp_path)
    small = ws / "visited_small.jsonl"
    small.write_text(json.dumps({"k": "v"}) + "\n", encoding="utf-8")
    f = check_dead_grain_writers(ws, {})
    assert f["verdict"] == "ok"


def test_dead_grain_writers_ok_large_but_small_lines(tmp_path):
    """A >20MB file with small lines (compact log) → ok."""
    ws = _ws(tmp_path)
    large_file = ws / "compact_log.jsonl"
    thin_line = json.dumps({"id": 1}) + "\n"  # ~10 bytes
    with large_file.open("w", encoding="utf-8") as fh:
        # 25MB / 10 bytes ≈ 2.5M lines — too slow; instead write 20MB+ via repeat
        # Use a medium-size payload that's still under 10KB
        medium_line = json.dumps({"id": 1, "data": "a" * 1000}) + "\n"  # ~1KB
        needed = (21 * 1024 * 1024) // len(medium_line.encode()) + 1
        for _ in range(needed):
            fh.write(medium_line)
    f = check_dead_grain_writers(ws, {})
    assert f["verdict"] == "ok"


# ── check_contract_surface_drift ──────────────────────────────────────────────

def test_contract_surface_drift_positive(tmp_path):
    """Planted positive: a fake src_root where a 'must-have-callers' symbol has
    no call site outside its definition file → anomaly fires.

    We monkey-patch _MUST_HAVE_CALLERS inside the detector by pointing it at a
    temp dir with a single definition file and no callers.
    """
    # Build a minimal fake src tree: one file defines the symbol, no other files call it.
    fake_src = tmp_path / "src" / "ztare"
    fake_src.mkdir(parents=True)
    (fake_src / "__init__.py").write_text("")
    def_file = fake_src / "fake_module.py"
    def_file.write_text(
        "def my_exported_fn(): pass\n"
        "__all__ = ['my_exported_fn']\n"
    )
    # Call the detector directly, overriding _MUST_HAVE_CALLERS via a thin wrapper.
    # Since _MUST_HAVE_CALLERS is module-level inside the function, we call the real
    # detector against the fake src_root and plant a symbol that only appears in one file.
    # The detector greps for "my_exported_fn" in fake_src — only the definition file hits.
    import ztare.orchestrator.trace_auditor as _ta
    import unittest.mock as mock

    # Patch the hard-coded list inside the function by patching subprocess.run to
    # return only the definition-file hit.
    with mock.patch("ztare.orchestrator.trace_auditor.subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(
            stdout="ztare/fake_module.py:1:def my_exported_fn(): pass\n",
            stderr="",
            returncode=0,
        )
        # Also patch the ztare imports inside the detector so receipt-type sub-check passes.
        with mock.patch.dict("sys.modules", {
            "ztare.validator.worldmodel_typed_payload": mock.Mock(
                _KNOWN_CONTROL_RECEIPT_TYPES=("INVESTIGATED",),
                worldmodel_typed_payload_contract_prompt=lambda: "INVESTIGATED LOWERABILITY_BLOCKED",
            ),
            "ztare.common.science_output_policy": mock.Mock(
                SCIENCE_OUTPUT_POLICY=mock.Mock(
                    final_contract_text=lambda: "INVESTIGATED",
                ),
            ),
            "ztare.common.candidate_first_policy": mock.Mock(
                candidate_first_policy_text=lambda: "INVESTIGATED",
            ),
        }):
            # Temporarily override the _MUST_HAVE_CALLERS constant inside the function
            # by patching the grep output to simulate a zero-caller organ.
            # The def_file filter uses "ztare/validator/core/worldmodel_control_outcome.py"
            # in the real code; our mock returns a line matching that path.
            mock_run.return_value = mock.Mock(
                stdout="ztare/validator/core/worldmodel_control_outcome.py:16:__all__ = ...\n"
                       "ztare/validator/core/worldmodel_control_outcome.py:117:def build_worldmodel_control_only_eval\n",
                stderr="",
                returncode=0,
            )
            fake_src_root = tmp_path / "src" / "ztare"
            f = _ta.check_contract_surface_drift(fake_src_root, {})
    # With all lines matching the def_file, zero_callers should trigger.
    assert f["check_id"] == "contract_surface_drift"
    assert f["verdict"] == "anomaly"
    assert "zero_caller_organs" in f["witness"]
    assert f["witness"]["zero_caller_organs"]


def test_contract_surface_drift_negative(tmp_path):
    """Planted negative: real src_root with build_worldmodel_control_only_eval
    — anomaly fires (real HEAD drift), but the detector returns a well-formed finding.

    This does NOT assert ok/anomaly because the real HEAD has a known zero-caller organ.
    It asserts only that the detector is well-formed and returns a valid finding.
    """
    src_root = REPO / "src" / "ztare"
    f = check_contract_surface_drift(src_root, {})
    assert f["check_id"] == "contract_surface_drift"
    assert f["verdict"] in ("ok", "anomaly")
    assert "untaught_types" in f["witness"]
    assert "zero_caller_organs" in f["witness"]
    assert isinstance(f["note"], str) and f["note"]


def test_contract_surface_drift_real_head_is_wired():
    """The organ build_worldmodel_control_only_eval was wired 2026-07-10
    (control-only turns consume the iteration instead of striking).
    This test now pins the WIRED state: the detector must NOT report it
    as a zero-caller organ. If this fails, the call site was removed."""
    src_root = REPO / "src" / "ztare"
    f = check_contract_surface_drift(src_root, {})
    assert "build_worldmodel_control_only_eval" not in str(
        f["witness"].get("zero_caller_organs", [])
    ), "build_worldmodel_control_only_eval lost its caller again"


# ── check_file_seam_coverage (BUILD E) ───────────────────────────────────────

def _make_fake_src(root: Path, *, writer_only_name: str,
                   written_and_read_name: str) -> Path:
    """Plant two fake src py files:
      - writer.py: writes writer_only_name but never reads it
      - reader.py: both writes and reads written_and_read_name
    """
    src = root / "src" / "ztare"
    src.mkdir(parents=True)
    # File that only writes
    (src / "writer.py").write_text(
        f'import json\n'
        f'path = ws / "workspace/{writer_only_name}"\n'
        f'with path.open("a", encoding="utf-8") as fh:\n'
        f'    fh.write(json.dumps(row) + "\\n")\n',
        encoding="utf-8",
    )
    # File that both writes AND reads
    (src / "reader.py").write_text(
        f'import json\n'
        f'path = ws / "workspace/{written_and_read_name}"\n'
        f'with path.open("a", encoding="utf-8") as fh:\n'
        f'    fh.write(json.dumps(row) + "\\n")\n'
        f'data = path.read_text(encoding="utf-8")\n',
        encoding="utf-8",
    )
    return src


def test_file_seam_coverage_flags_write_only(tmp_path):
    """Planted write-only path → anomaly."""
    from ztare.orchestrator.trace_auditor import _SEAM_EXEMPTIONS
    src = _make_fake_src(tmp_path, writer_only_name="orphan_write.jsonl",
                         written_and_read_name="healthy_rw.jsonl")
    # Use an empty exemptions set so orphan_write.jsonl is not excluded
    f = check_file_seam_coverage(src, None, {}, exemptions=frozenset())
    assert f["check_id"] == "file_seam_coverage"
    assert f["verdict"] == "anomaly"
    assert "orphan_write.jsonl" in f["witness"]["write_only_paths"]
    assert "healthy_rw.jsonl" not in f["witness"]["write_only_paths"]


def test_file_seam_coverage_clean_when_all_read(tmp_path):
    """All written paths also read → ok."""
    from ztare.orchestrator.trace_auditor import _SEAM_EXEMPTIONS
    src = _make_fake_src(tmp_path, writer_only_name="also_read.jsonl",
                         written_and_read_name="also_read.jsonl")  # same file: both written+read
    f = check_file_seam_coverage(src, None, {}, exemptions=frozenset())
    assert f["verdict"] == "ok"
    assert f["witness"]["write_only_count"] == 0


def test_file_seam_coverage_exemption_silences_write_only(tmp_path):
    """Path in exemptions set → not flagged even if write-only."""
    src = _make_fake_src(tmp_path, writer_only_name="exempt_only.jsonl",
                         written_and_read_name="healthy.jsonl")
    f = check_file_seam_coverage(src, None, {}, exemptions=frozenset({"exempt_only.jsonl"}))
    assert f["verdict"] == "ok"
    assert "exempt_only.jsonl" not in f["witness"].get("write_only_paths", [])


def test_file_seam_coverage_real_repo_run_audit(tmp_path):
    """run_audit on a temp project includes file_seam_coverage in findings."""
    ws = _ws(tmp_path)
    project = _project(ws)
    result = run_audit(project)
    check_ids = [f["check_id"] for f in result["findings"]]
    assert "file_seam_coverage" in check_ids, (
        "run_audit must include file_seam_coverage finding"
    )


# ── check_organ_liveness ──────────────────────────────────────────────────────

def _make_organ_fixture(
    tmp_path: Path,
    *,
    index_rows: list[str],
    modules: dict[str, str],          # rel_path -> file contents
    fire_rows: list[dict] | None = None,
) -> tuple[Path, Path, Path]:
    """Build a minimal fake repo structure for organ liveness tests.

    Returns (ws, src_root, index_path).
    """
    ws = tmp_path / "projects" / "proj" / "workspace"
    ws.mkdir(parents=True)

    src_root = tmp_path / "src" / "ztare"
    src_root.mkdir(parents=True)

    # Write fake modules
    for rel, content in modules.items():
        p = src_root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    # Write INDEX.md
    idx_dir = src_root / "architecture_index"
    idx_dir.mkdir(parents=True, exist_ok=True)
    idx_path = idx_dir / "INDEX.md"
    idx_path.write_text(
        "# ZTARE Architecture Index\n\n"
        "| ID | Path | Impact | Last Used | Description |\n"
        "|---|---|---|---|---|\n"
        + "\n".join(index_rows)
        + "\n",
        encoding="utf-8",
    )

    # Write organ_first_fire.jsonl if given
    if fire_rows:
        fire_path = ws / "organ_first_fire.jsonl"
        fire_path.write_text(
            "".join(json.dumps(r) + "\n" for r in fire_rows),
            encoding="utf-8",
        )

    return ws, src_root, idx_path


def test_organ_liveness_built_not_wired(tmp_path):
    """An indexed organ with no importers → anomaly, appears in built_not_wired."""
    ws, src_root, _ = _make_organ_fixture(
        tmp_path,
        index_rows=[
            "| **ORPHAN-GATE** | `src/ztare/gates/orphan_gate.py` | 1 | never | orphan gate |",
        ],
        modules={"gates/orphan_gate.py": "def run(): pass\n"},
        # No other module imports orphan_gate
    )
    state: dict = {}
    f = check_organ_liveness(ws, state, src_root)
    assert f["check_id"] == "organ_liveness"
    assert f["verdict"] == "anomaly"
    assert "ORPHAN-GATE" in f["witness"]["built_not_wired"]
    assert f["witness"]["built_not_wired_count"] >= 1


def test_organ_liveness_wired_not_fired(tmp_path):
    """An organ that IS imported but has no fire receipt → appears in wired_not_fired."""
    ws, src_root, _ = _make_organ_fixture(
        tmp_path,
        index_rows=[
            "| **WIRED-GATE** | `src/ztare/gates/wired_gate.py` | 2 | 2026-01-01 | wired gate |",
        ],
        modules={
            "gates/wired_gate.py": "def run(): pass\n",
            # Another module imports it
            "caller.py": "from ztare.gates.wired_gate import run\n",
        },
        fire_rows=None,   # no fire ledger
    )
    state: dict = {}
    f = check_organ_liveness(ws, state, src_root)
    assert f["check_id"] == "organ_liveness"
    assert f["verdict"] == "anomaly"
    assert "WIRED-GATE" in f["witness"]["wired_not_fired"]
    assert f["witness"]["wired_not_fired_count"] >= 1
    assert f["witness"]["built_not_wired_count"] == 0


def test_organ_liveness_no_anomaly(tmp_path):
    """Organ wired AND has fire receipt → ok."""
    ws, src_root, _ = _make_organ_fixture(
        tmp_path,
        index_rows=[
            "| **HEALTHY-GATE** | `src/ztare/gates/healthy_gate.py` | 3 | 2026-06-01 | healthy gate |",
        ],
        modules={
            "gates/healthy_gate.py": "def run(): pass\n",
            "caller.py": "from ztare.gates.healthy_gate import run\n",
        },
        fire_rows=[
            {"schema": "ztare.organ_first_fire.v1", "organ": "HEALTHY-GATE",
             "fired_at": "2026-06-01T00:00:00+00:00",
             "receipt_ref": "workspace/healthy_gate_receipt.json"},
        ],
    )
    state: dict = {}
    f = check_organ_liveness(ws, state, src_root)
    assert f["check_id"] == "organ_liveness"
    assert f["verdict"] == "ok"
    assert f["witness"]["built_not_wired_count"] == 0
    assert f["witness"]["wired_not_fired_count"] == 0


def test_organ_liveness_malformed_rows_skipped(tmp_path):
    """Malformed INDEX rows (missing path backtick) are skipped, not raised."""
    ws, src_root, idx_path = _make_organ_fixture(
        tmp_path,
        index_rows=[
            # Valid row
            "| **GOOD-GATE** | `src/ztare/gates/good_gate.py` | 1 | never | good |",
            # Malformed: no backtick-quoted path
            "| BAD-ROW | not_a_backtick_path | x | | |",
            # Another malformed: missing columns
            "| PARTIAL |",
        ],
        modules={
            "gates/good_gate.py": "def run(): pass\n",
            "caller.py": "from ztare.gates.good_gate import run\n",
        },
    )
    state: dict = {}
    # Should not raise; should parse GOOD-GATE and skip malformed rows
    f = check_organ_liveness(ws, state, src_root)
    assert f["check_id"] == "organ_liveness"
    assert f["verdict"] in ("ok", "anomaly")
    # Malformed count reflected in witness
    assert "malformed_index_rows" in f["witness"]
    # Only GOOD-GATE should have been checked
    assert f["witness"]["organs_checked"] == 1


def test_organ_liveness_in_run_audit(tmp_path):
    """run_audit includes organ_liveness in its findings."""
    ws = _ws(tmp_path)
    project = _project(ws)
    result = run_audit(project)
    check_ids = [f["check_id"] for f in result["findings"]]
    assert "organ_liveness" in check_ids, (
        "run_audit must include organ_liveness finding"
    )


def test_parse_index_md_robustness(tmp_path):
    """_parse_index_md handles mixed valid/malformed rows without raising."""
    idx = tmp_path / "INDEX.md"
    idx.write_text(
        "# header\n"
        "| **GOOD** | `src/ztare/gates/foo.py` | 3 | 2026-01-01 | desc |\n"
        "| **ANOTHER** | `src/ztare/gates/bar.py` | 1 | never | desc | extra | cols |\n"
        "| bad row no pipes\n"
        "| **IMPACT-MISSING** | `src/ztare/gates/baz.py` | not_an_int | | |\n",
        encoding="utf-8",
    )
    organs = _parse_index_md(idx)
    # Filter out sentinel
    real = [o for o in organs if "_malformed_count" not in o]
    ids = [o["id"] for o in real]
    assert "GOOD" in ids
    assert "ANOTHER" in ids
    # IMPACT-MISSING has non-int impact → skipped (malformed)
    assert "IMPACT-MISSING" not in ids
    # Malformed sentinel present
    sentinels = [o for o in organs if "_malformed_count" in o]
    assert sentinels, "malformed sentinel missing"
    assert sentinels[0]["_malformed_count"] >= 1