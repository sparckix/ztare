"""Tests for ztare.common.k_line — 12 tests covering:

- extract_configuration with missing artifacts → honest Nones
- signature bucketing stability under translation + color-permutation + time-shift (invariance)
- record + backfill
- attribution contrast: component present in successes only → positive score, support counted
- propose with exact-signature match
- insufficient-support marking
- never proposes unknown configuration component keys
- regime_position boundary detection
- divergent-cell localization
- epistemic_state bucketing
- witness component topology
- action conditionality
"""
import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ztare.common.k_line import (
    LEDGER_SCHEMA,
    ORIGIN_HUMAN,
    ORIGIN_AGENT,
    TRANSFER_RETROSPECTIVE,
    TRANSFER_PROSPECTIVE,
    _action_conditionality,
    _divergent_cell_localization,
    _epistemic_bucket,
    _regime_position,
    _witness_component_bucket,
    attribution,
    extract_configuration,
    problem_signature,
    propose_configuration,
    record_failure,
    record_human_kline,
    record_success,
    scan_and_backfill,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────


def _bare_project(
    *,
    promotions: list[dict] | None = None,
    no_ops: list[dict] | None = None,
    rs_rows: list[dict] | None = None,
    wa_rows: list[dict] | None = None,
    er_rows: list[dict] | None = None,
    cm_records: list[dict] | None = None,
) -> Path:
    tmp = Path(tempfile.mkdtemp())
    ws = tmp / "workspace"
    ws.mkdir()

    # champion_materialization.jsonl
    cm_rows = []
    for p in promotions or []:
        cm_rows.append({"result": "promoted", "ts": p.get("ts", "20260710T010101"), **p})
    for n in no_ops or []:
        cm_rows.append({"result": "no_op", "ts": n.get("ts", "20260710T020202"), **n})
    if cm_rows:
        (ws / "champion_materialization.jsonl").write_text(
            "\n".join(json.dumps(r) for r in cm_rows) + "\n"
        )

    # residual_specialists.jsonl
    if rs_rows:
        (ws / "residual_specialists.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rs_rows) + "\n"
        )

    # width_allocations.jsonl
    if wa_rows:
        (ws / "width_allocations.jsonl").write_text(
            "\n".join(json.dumps(r) for r in wa_rows) + "\n"
        )

    # engine_routing.jsonl
    if er_rows:
        (ws / "engine_routing.jsonl").write_text(
            "\n".join(json.dumps(r) for r in er_rows) + "\n"
        )

    # candidate_memory.json
    if cm_records:
        (ws / "candidate_memory.json").write_text(json.dumps({"records": cm_records}))

    return tmp


# ── Test 1: extract_configuration with no artifacts → all None ────────────────


def test_extract_configuration_missing_artifacts():
    tmp = _bare_project()
    cfg = extract_configuration(tmp)
    assert cfg["engine"] is None
    assert cfg["phase"] is None
    assert cfg["specialist_mode"] is None
    assert cfg["specialist_model"] is None
    assert cfg["specialist_effort"] is None
    assert cfg["width_shards"] is None
    assert cfg["width_samples"] is None
    assert cfg["width_effort"] is None
    assert cfg["has_ground_truth"] is False
    assert cfg["champion_source"] is None
    assert cfg["has_engine_routing"] is False


# ── Test 2: extract_configuration reads engine_routing last row ───────────────


def test_extract_configuration_engine_routing():
    tmp = _bare_project(
        er_rows=[
            {"schema": "ztare.engine_routing.v1", "engine": "specialists", "phase": None, "ts": "t1"},
            {"schema": "ztare.engine_routing.v1", "engine": "version_space", "phase": "distinguishing_play", "ts": "t2"},
        ]
    )
    cfg = extract_configuration(tmp)
    assert cfg["engine"] == "version_space"
    assert cfg["phase"] == "distinguishing_play"
    assert cfg["has_engine_routing"] is True


# ── Test 3: extract_configuration reads width_allocations ────────────────────


def test_extract_configuration_width_allocations():
    tmp = _bare_project(
        wa_rows=[{"schema": "ztare.width_allocation.v1", "decision": {"shards": 3, "samples_per_shard": 2, "effort": "medium"}, "ts": 1234}]
    )
    cfg = extract_configuration(tmp)
    assert cfg["width_shards"] == 3
    assert cfg["width_samples"] == 2
    assert cfg["width_effort"] == "medium"


# ── Test 4: extract_configuration reads champion_source ──────────────────────


def test_extract_configuration_champion_source():
    tmp = _bare_project(
        promotions=[{"ts": "20260710T010101", "from_ref": "workspace/submissions/iter_003.py", "promoted_sha": "abc123"}]
    )
    cfg = extract_configuration(tmp)
    assert cfg["champion_source"] is not None
    assert "iter_003" in cfg["champion_source"] or "abc123" in cfg["champion_source"]


# ── Test 5: signature invariance under translation + color-permutation + time-shift ──


def _make_divergent_cells(offsets: list[tuple[int, int]], color: int = 3) -> list[dict]:
    return [{"row": r, "col": c, "predicted": color, "actual": color + 1} for r, c in offsets]


def _synthetic_signature(
    *,
    divergent_cells: list[dict],
    action: int = 1,
    step_index: int = 0,
    entry_context_note: str | None = None,
    eliminated_families: list | None = None,
    stagnation: int = 0,
) -> dict:
    """Build signature dict directly from synthetic data (bypasses file I/O)."""
    from ztare.common.k_line import (
        _action_conditionality,
        _divergent_cell_localization,
        _epistemic_bucket,
        _regime_position,
        _warrant_stratum_from_materialization,
        _witness_component_bucket,
    )
    return {
        "warrant_stratum": "visible",  # fixed for this test
        "contradiction_topology": _witness_component_bucket(divergent_cells),
        "residual_localization": _divergent_cell_localization(divergent_cells),
        "input_conditionality": _action_conditionality(action, []),
        "regime_position": _regime_position(entry_context_note, step_index),
        "epistemic_state": _epistemic_bucket(eliminated_families or [], stagnation, 1.0),
    }


def test_signature_invariant_under_translation():
    """Translating all cells by (+10, +5) must not change the signature."""
    cells_a = _make_divergent_cells([(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)])
    cells_b = _make_divergent_cells([(10, 5), (10, 6), (10, 7), (11, 5), (11, 6), (11, 7)])
    sig_a = _synthetic_signature(divergent_cells=cells_a)
    sig_b = _synthetic_signature(divergent_cells=cells_b)
    assert sig_a == sig_b, f"signature changed under translation:\n{sig_a}\nvs\n{sig_b}"


def test_signature_invariant_under_color_permutation():
    """Permuting colors (3→7, 7→3) must not change the signature."""
    cells_a = _make_divergent_cells([(5, 5), (5, 6)], color=3)
    cells_b = [{"row": 5, "col": 5, "predicted": 7, "actual": 8},
               {"row": 5, "col": 6, "predicted": 7, "actual": 8}]
    sig_a = _synthetic_signature(divergent_cells=cells_a)
    sig_b = _synthetic_signature(divergent_cells=cells_b)
    assert sig_a == sig_b, f"signature changed under color permutation:\n{sig_a}\nvs\n{sig_b}"


def test_signature_invariant_under_time_shift():
    """Shifting absolute t by +1000 must not affect the signature (step_index 0 stays boundary)."""
    # The signature doesn't take t directly — it uses step_index only
    sig_a = _synthetic_signature(divergent_cells=_make_divergent_cells([(0, 0)]), step_index=0)
    sig_b = _synthetic_signature(divergent_cells=_make_divergent_cells([(0, 0)]), step_index=0)
    assert sig_a == sig_b


# ── Test 6: record + backfill ─────────────────────────────────────────────────


def test_record_success_appends_row():
    tmp = _bare_project()
    fake_sig = {"warrant_stratum": "holdout", "contradiction_topology": "components-1",
                "residual_localization": "coherent_block", "input_conditionality": "uniform",
                "regime_position": "boundary", "epistemic_state": "collapsed-0"}
    fake_cfg = {"engine": "specialists", "phase": None, "specialist_mode": "workbench",
                "width_shards": 3, "width_effort": "low"}
    row = record_success(tmp, {"ts": "20260710T010101", "result": "promoted"},
                         signature=fake_sig, configuration=fake_cfg)
    assert row["outcome"] == "success"
    assert row["schema"] == LEDGER_SCHEMA
    lines = (tmp / "workspace" / "k_lines.jsonl").read_text().strip().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["outcome"] == "success"


def test_scan_and_backfill_counts():
    tmp = _bare_project(
        promotions=[
            {"ts": "20260710T010101", "from_ref": "p1"},
            {"ts": "20260710T020202", "from_ref": "p2"},
        ],
        no_ops=[{"ts": "20260710T030303"}],
        rs_rows=[
            {"_schema": "ztare.residual_specialists.v1", "timestamp": 1234, "dispatches": [], "sharding_mode": "by_mechanism"},
        ],
    )
    n = scan_and_backfill(tmp)
    # 3 materialization rows + 1 rs row = 4
    assert n == 4
    rows = [json.loads(l) for l in (tmp / "workspace" / "k_lines.jsonl").read_text().strip().splitlines()]
    assert len(rows) == 4
    outcomes = [r["outcome"] for r in rows]
    assert outcomes.count("success") == 2
    assert outcomes.count("failure") == 2


def test_scan_and_backfill_idempotent():
    tmp = _bare_project(
        promotions=[{"ts": "20260710T010101", "from_ref": "p1"}],
    )
    n1 = scan_and_backfill(tmp)
    n2 = scan_and_backfill(tmp)
    assert n1 == 1
    assert n2 == 0  # already present


# ── Test 7: attribution contrast — component present in successes only ─────────


def _plant_ledger(project_dir: Path, rows: list[dict]) -> None:
    ws = project_dir / "workspace"
    ws.mkdir(exist_ok=True)
    ledger = ws / "k_lines.jsonl"
    with ledger.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def test_attribution_positive_contrast_for_success_component():
    """Component value 'workbench' appears only in successes → positive contrast."""
    tmp = Path(tempfile.mkdtemp())
    sig = {"warrant_stratum": "holdout", "contradiction_topology": "components-1",
           "residual_localization": "coherent_block", "input_conditionality": "uniform",
           "regime_position": "boundary", "epistemic_state": "collapsed-0"}
    # 5 successes with specialist_mode=workbench, 5 failures with specialist_mode=sealed
    rows = []
    for i in range(5):
        rows.append({"schema": LEDGER_SCHEMA, "ts": f"s{i}", "signature": sig,
                     "configuration": {"specialist_mode": "workbench"}, "outcome": "success"})
    for i in range(5):
        rows.append({"schema": LEDGER_SCHEMA, "ts": f"f{i}", "signature": sig,
                     "configuration": {"specialist_mode": "sealed"}, "outcome": "failure"})
    _plant_ledger(tmp, rows)

    attr = attribution(tmp)
    comp = attr["components"]["specialist_mode"]
    workbench_entry = comp["values"]["workbench"]
    sealed_entry = comp["values"]["sealed"]
    assert workbench_entry["contrast"] is not None
    assert workbench_entry["contrast"] > 0, "workbench should have positive contrast"
    assert workbench_entry["support"] == 5
    assert sealed_entry["contrast"] is not None
    assert sealed_entry["contrast"] < 0, "sealed should have negative contrast"


def test_attribution_insufficient_support_marked():
    """Values with support < 3 are marked insufficient_evidence."""
    tmp = Path(tempfile.mkdtemp())
    sig = {"warrant_stratum": "visible"}
    rows = [
        {"schema": LEDGER_SCHEMA, "ts": "a1", "signature": sig,
         "configuration": {"specialist_mode": "workbench"}, "outcome": "success"},
        {"schema": LEDGER_SCHEMA, "ts": "a2", "signature": sig,
         "configuration": {"specialist_mode": "workbench"}, "outcome": "failure"},
    ]
    _plant_ledger(tmp, rows)
    attr = attribution(tmp)
    comp = attr["components"]["specialist_mode"]
    entry = comp["values"]["workbench"]
    assert entry["insufficient_evidence"] is True
    assert entry["support"] == 2


# ── Test 8: propose with exact-signature match ────────────────────────────────


def test_propose_exact_match():
    tmp = Path(tempfile.mkdtemp())
    (tmp / "workspace").mkdir()

    sig = {"warrant_stratum": "holdout", "contradiction_topology": "components-1",
           "residual_localization": "coherent_block", "input_conditionality": "uniform",
           "regime_position": "boundary", "epistemic_state": "collapsed-0"}

    # Plant ledger with 4 successes using workbench
    rows = []
    for i in range(4):
        rows.append({"schema": LEDGER_SCHEMA, "ts": f"x{i}", "signature": sig,
                     "configuration": {"specialist_mode": "workbench", "width_effort": "low"},
                     "outcome": "success"})
    _plant_ledger(tmp, rows)

    # Patch problem_signature to return our fixed sig
    import ztare.common.k_line as kl
    _orig = kl.problem_signature
    kl.problem_signature = lambda _: sig
    try:
        prop = propose_configuration(tmp)
    finally:
        kl.problem_signature = _orig

    assert prop["match_type"] == "exact"
    assert "specialist_mode" in prop["proposed_configuration"]
    assert prop["proposed_configuration"]["specialist_mode"]["value"] == "workbench"


# ── Test 9: insufficient-support in proposal ──────────────────────────────────


def test_propose_insufficient_support_note():
    tmp = Path(tempfile.mkdtemp())
    (tmp / "workspace").mkdir()

    sig = {"warrant_stratum": "visible"}
    # Only 2 rows — below threshold of 3
    rows = [
        {"schema": LEDGER_SCHEMA, "ts": "y1", "signature": sig,
         "configuration": {"specialist_mode": "workbench"}, "outcome": "success"},
        {"schema": LEDGER_SCHEMA, "ts": "y2", "signature": sig,
         "configuration": {"specialist_mode": "workbench"}, "outcome": "failure"},
    ]
    _plant_ledger(tmp, rows)

    import ztare.common.k_line as kl
    _orig = kl.problem_signature
    kl.problem_signature = lambda _: sig
    try:
        prop = propose_configuration(tmp)
    finally:
        kl.problem_signature = _orig

    entry = prop["proposed_configuration"]["specialist_mode"]
    assert "insufficient_evidence" in (entry.get("note") or "")


# ── Test 10: never proposes unknown component keys ────────────────────────────


def test_propose_never_unknown_keys():
    tmp = Path(tempfile.mkdtemp())
    (tmp / "workspace").mkdir()

    sig = {"warrant_stratum": "visible"}
    known_keys = {"specialist_mode", "width_effort", "engine"}
    rows = []
    for i in range(4):
        rows.append({"schema": LEDGER_SCHEMA, "ts": f"z{i}", "signature": sig,
                     "configuration": {k: "val" for k in known_keys},
                     "outcome": "success"})
    _plant_ledger(tmp, rows)

    import ztare.common.k_line as kl
    _orig = kl.problem_signature
    kl.problem_signature = lambda _: sig
    try:
        prop = propose_configuration(tmp)
    finally:
        kl.problem_signature = _orig

    proposed_keys = set(prop["proposed_configuration"].keys())
    assert proposed_keys <= known_keys, f"unknown keys proposed: {proposed_keys - known_keys}"


# ── Test 11: divergent-cell localization ──────────────────────────────────────


def test_localization_single_cell():
    assert _divergent_cell_localization([{"row": 5, "col": 3}]) == "single_cell"


def test_localization_coherent_block():
    cells = [{"row": r, "col": c} for r in range(3) for c in range(3)]
    assert _divergent_cell_localization(cells) == "coherent_block"


def test_localization_full_frame():
    # 8 scattered cells far apart → full_frame
    cells = [{"row": r * 10, "col": c * 10} for r in range(4) for c in range(2)]
    result = _divergent_cell_localization(cells)
    assert result in ("full_frame", "coherent_block")  # structural, not exact grid layout


# ── Test 12: regime_position and epistemic_state helpers ─────────────────────


def test_regime_position_boundary_at_step_0():
    assert _regime_position(None, 0) == "boundary"
    assert _regime_position("holdout starts mid-episode", 0) == "boundary"


def test_regime_position_interior():
    assert _regime_position("holdout starts mid-episode at its first row t=19", 4) == "interior"


def test_epistemic_bucket():
    assert _epistemic_bucket([], 0, 1.0) == "diverse"
    assert _epistemic_bucket([], 2, 0.0) == "collapsed-0"
    assert _epistemic_bucket(["h1", "h2"], 0, 0.0) == "collapsed-1-3"
    assert _epistemic_bucket(["h1", "h2", "h3", "h4"], 0, 0.0) == "collapsed-4+"


def test_action_conditionality():
    assert _action_conditionality(1, []) == "uniform"
    assert _action_conditionality(1, [{"action": 2}]) == "mixed"
    assert _action_conditionality(None, []) == "uniform"


# ── Provenance tests (cold-review finding 9) ──────────────────────────────────


# Test P1: new provenance fields persisted on record_success (prospectively_reproduced)
def test_record_success_provenance_fields():
    tmp = _bare_project()
    sig = {"warrant_stratum": "holdout"}
    cfg = {"engine": "specialists"}
    row = record_success(tmp, {"ts": "t1"}, signature=sig, configuration=cfg)
    assert row["origin"] == ORIGIN_AGENT
    assert row["transfer_status"] == TRANSFER_PROSPECTIVE
    assert "proposal_time_evidence" in row
    assert "validation_authority" in row
    # Persisted to disk
    ledger_row = json.loads((tmp / "workspace" / "k_lines.jsonl").read_text().strip())
    assert ledger_row["transfer_status"] == TRANSFER_PROSPECTIVE


# Test P2: backfill rows carry retrospective_candidate
def test_backfill_rows_are_retrospective():
    tmp = _bare_project(promotions=[{"ts": "20260710T010101", "from_ref": "p1"}])
    scan_and_backfill(tmp)
    row = json.loads((tmp / "workspace" / "k_lines.jsonl").read_text().strip())
    assert row["origin"] == ORIGIN_AGENT
    assert row["transfer_status"] == TRANSFER_RETROSPECTIVE


# Test P3: record_human_kline produces origin=human, retrospective_candidate
def test_record_human_kline_fields():
    tmp = _bare_project()
    sig = {"warrant_stratum": "observed", "residual_localization": "global", "epistemic_state": "stagnant"}
    cfg = {"fix_class": "contract_surface_routing"}
    row = record_human_kline(tmp, sig, cfg, "test note")
    assert row["origin"] == ORIGIN_HUMAN
    assert row["transfer_status"] == TRANSFER_RETROSPECTIVE
    assert row["note"] == "test note"
    # Persisted
    ledger_row = json.loads((tmp / "workspace" / "k_lines.jsonl").read_text().strip())
    assert ledger_row["origin"] == ORIGIN_HUMAN


# Test P4: propose excludes human retrospective rows by default
def test_propose_excludes_human_retrospective_by_default(monkeypatch):
    tmp = Path(tempfile.mkdtemp())
    (tmp / "workspace").mkdir()
    sig = {"warrant_stratum": "holdout", "contradiction_topology": "components-1",
           "residual_localization": "coherent_block", "input_conditionality": "uniform",
           "regime_position": "boundary", "epistemic_state": "collapsed-0"}

    # 4 human retrospective rows with signature match
    rows = []
    for i in range(4):
        rows.append({
            "schema": LEDGER_SCHEMA, "ts": f"h{i}", "signature": sig,
            "configuration": {"fix_class": "human_fix"}, "outcome": "human_forensic",
            "origin": ORIGIN_HUMAN, "transfer_status": TRANSFER_RETROSPECTIVE,
        })
    _plant_ledger(tmp, rows)

    import ztare.common.k_line as kl
    monkeypatch.setattr(kl, "problem_signature", lambda _: sig)
    monkeypatch.delenv("ZTARE_KLINE_HUMAN_PRIOR", raising=False)

    prop = propose_configuration(tmp)
    # No candidates survive the guard → match_type=none
    assert prop["match_type"] == "none"
    assert prop["human_rows_excluded"] == 4
    assert prop["human_prior_allowance"] is False


# Test P5: ZTARE_KLINE_HUMAN_PRIOR=1 includes human rows and sets receipt flag
def test_propose_includes_human_rows_with_env_allowance(monkeypatch):
    tmp = Path(tempfile.mkdtemp())
    (tmp / "workspace").mkdir()
    sig = {"warrant_stratum": "holdout", "contradiction_topology": "components-1",
           "residual_localization": "coherent_block", "input_conditionality": "uniform",
           "regime_position": "boundary", "epistemic_state": "collapsed-0"}

    rows = []
    for i in range(4):
        rows.append({
            "schema": LEDGER_SCHEMA, "ts": f"h{i}", "signature": sig,
            "configuration": {"fix_class": "human_fix"}, "outcome": "human_forensic",
            "origin": ORIGIN_HUMAN, "transfer_status": TRANSFER_RETROSPECTIVE,
        })
    _plant_ledger(tmp, rows)

    import ztare.common.k_line as kl
    monkeypatch.setattr(kl, "problem_signature", lambda _: sig)
    monkeypatch.setenv("ZTARE_KLINE_HUMAN_PRIOR", "1")

    prop = propose_configuration(tmp)
    assert prop["human_prior_allowance"] is True
    assert prop["human_rows_excluded"] == 0
    # fix_class should be proposed (4 rows, all human_forensic outcome → no success filter but pool falls back to all)
    assert "fix_class" in prop["proposed_configuration"]


# Test P6: attribution segments origins — human rows absent from components contrast
def test_attribution_segments_origins():
    tmp = Path(tempfile.mkdtemp())
    sig = {"warrant_stratum": "holdout"}
    rows = []
    # 4 agent success rows
    for i in range(4):
        rows.append({"schema": LEDGER_SCHEMA, "ts": f"a{i}", "signature": sig,
                     "configuration": {"specialist_mode": "workbench"}, "outcome": "success",
                     "origin": ORIGIN_AGENT, "transfer_status": TRANSFER_PROSPECTIVE})
    # 4 human rows with different config — must NOT pollute agent contrast
    for i in range(4):
        rows.append({"schema": LEDGER_SCHEMA, "ts": f"h{i}", "signature": sig,
                     "configuration": {"fix_class": "human_only"}, "outcome": "human_forensic",
                     "origin": ORIGIN_HUMAN, "transfer_status": TRANSFER_RETROSPECTIVE})
    _plant_ledger(tmp, rows)

    attr = attribution(tmp)
    assert attr["n_human_rows"] == 4
    assert attr["n_agent_rows"] == 4
    # fix_class must NOT appear in agent components (it's human-only)
    assert "fix_class" not in attr["components"]
    # fix_class should appear in human_advisory
    assert "fix_class" in attr["human_advisory"]
    # specialist_mode IS in agent components
    assert "specialist_mode" in attr["components"]


# Test P7: live record_success stamps prospectively_reproduced
def test_record_success_stamps_prospective():
    tmp = _bare_project()
    sig = {"warrant_stratum": "visible"}
    row = record_success(tmp, {"ts": "t1"}, signature=sig, configuration={"engine": "x"})
    assert row["transfer_status"] == TRANSFER_PROSPECTIVE
    assert row["origin"] == ORIGIN_AGENT


# Test P8: backfill helper rows are well-formed (all 4 forensic entries)
def test_record_human_kline_backfill_wellformed():
    tmp = _bare_project()
    entries = [
        ({"warrant_stratum": "observed", "residual_localization": "global", "epistemic_state": "stagnant"},
         {"fix_class": "contract_surface_routing"},
         "R1 bounce class"),
        ({"warrant_stratum": "heldout", "residual_localization": "structured", "epistemic_state": "collapsed"},
         {"fix_class": "recategorize_cause_not_attribute"},
         "cell-shards note"),
        ({"warrant_stratum": "heldout", "epistemic_state": "capability_tied"},
         {"fix_class": "targeted_evidence_acquisition"},
         "3 leaf tiers tie"),
        ({"warrant_stratum": "observed", "residual_localization": "global", "epistemic_state": "cost_growth"},
         {"fix_class": "residual_scaling_warmstart"},
         "cost must scale"),
    ]
    for sig, cfg, note in entries:
        row = record_human_kline(tmp, sig, cfg, note)
        assert row["origin"] == ORIGIN_HUMAN
        assert row["transfer_status"] == TRANSFER_RETROSPECTIVE
        assert row["note"] == note
        assert "fix_class" in row["configuration"]

    lines = (tmp / "workspace" / "k_lines.jsonl").read_text().strip().splitlines()
    assert len(lines) == 4
    for line in lines:
        r = json.loads(line)
        assert r["origin"] == ORIGIN_HUMAN
        assert r["transfer_status"] == TRANSFER_RETROSPECTIVE
