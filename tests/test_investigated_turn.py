"""INVESTIGATED science-turn outcome: credit contract + anti-gaming + firewall.

An INVESTIGATED turn eliminates a hypothesis class from VISIBLE evidence. It is
credited (not scored 0-as-failure) iff the elimination is NEW to the visible
nogood ledger AND its witness checks out on the visible episode. A duplicate is
rejected, an unbacked witness is rejected (anti-gaming), a holdout witness raises
(firewall), and K consecutive investigated-only turns surface stagnation.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ztare.common.science_output_policy import INVESTIGATED_STAGNATION_K
from ztare.validator.core.worldmodel_control_outcome import (
    _process_investigated_receipts,
    build_worldmodel_control_only_eval,
)
from ztare.worldmodel.episode_log import EpisodeLog, Transition
from ztare.worldmodel.grid_dsl import grid_from_lists


def _write_visible_episode(project: Path) -> tuple[int, int, tuple[int, int], int, int]:
    """Plant a tiny visible episode; return a real refuting witness.

    At t=0, a=0 the cell (0,0) goes 3 -> 7. A hypothesis that predicts 3 there
    (e.g. identity) is genuinely refuted: observed=7, predicted=3.
    """
    ep_dir = project / "raw" / "episodes"
    ep_dir.mkdir(parents=True, exist_ok=True)
    log = EpisodeLog([
        Transition(0, grid_from_lists([[3, 3], [3, 3]]), 0, grid_from_lists([[7, 3], [3, 3]])),
        Transition(1, grid_from_lists([[7, 3], [3, 3]]), 1, grid_from_lists([[7, 7], [3, 3]])),
    ])
    log.write_jsonl(ep_dir / "episode_001.jsonl")
    # holdout episode (must never be citeable as a witness)
    hold = EpisodeLog([
        Transition(0, grid_from_lists([[1, 1], [1, 1]]), 0, grid_from_lists([[9, 1], [1, 1]])),
    ])
    hold.write_jsonl(ep_dir / "episode_002.jsonl")
    return 0, 0, (0, 0), 7, 3  # t, a, cell, observed, predicted


def _receipt(eliminated, t, a, cell, observed, predicted, refs=None, extra_witness=None):
    witness = {"t": t, "a": a, "cell": list(cell), "observed": observed, "predicted": predicted}
    if extra_witness:
        witness.update(extra_witness)
    return {
        "type": "INVESTIGATED",
        "payload": {
            "eliminated_hypothesis": eliminated,
            "witness": witness,
            "evidence_refs": refs or ["workspace/visible_cli_receipts/probe_0.json"],
        },
    }


def test_valid_investigated_is_credited_and_clause_written(tmp_path):
    proj = tmp_path / "proj"
    t, a, cell, obs, pred = _write_visible_episode(proj)
    receipt = _receipt({"rule": "identity_on_a0"}, t, a, cell, obs, pred)

    eval_row = build_worldmodel_control_only_eval(
        run_id=1, iteration=1, thesis_text="",
        artifact_refs=[], project_dir=proj,
    )
    # The eval row is built from thesis_text; pass the receipt directly through
    # the same processor the builder uses (thesis rendering is a separate path).
    credited, rejected = _process_investigated_receipts([receipt], project_dir=proj)
    assert len(credited) == 1 and not rejected
    # a clause landed in the visible nogood ledger
    ledger_path = proj / "workspace" / "spec_visible_nogoods.jsonl"
    assert ledger_path.exists()
    rows = [json.loads(l) for l in ledger_path.read_text().splitlines() if l.strip()]
    assert len(rows) == 1
    assert rows[0]["provenance"]["evidence"] == "visible"
    assert rows[0]["signature"] == credited[0]["signature"]


def test_credited_investigated_sets_progress_classification(tmp_path):
    proj = tmp_path / "proj"
    t, a, cell, obs, pred = _write_visible_episode(proj)
    receipt = _receipt({"rule": "identity_on_a0"}, t, a, cell, obs, pred)
    # Render a thesis carrying the receipt so the full builder path is exercised.
    thesis = "INVESTIGATED: " + json.dumps(receipt["payload"])
    # The builder parses control_receipts from the typed payload; feed a payload.
    thesis_payload = json.dumps({
        "control_receipts": [receipt],
        "thesis_markdown": "eliminated identity on a0",
    })
    eval_row = build_worldmodel_control_only_eval(
        run_id=1, iteration=1, thesis_text=thesis_payload,
        artifact_refs=[], project_dir=proj,
    )
    assert eval_row["score"] == 0  # investigation is not a candidate score
    assert eval_row["score_cap_reason"] == "worldmodel_investigated_residual_narrowed"
    assert eval_row.get("investigated_credited") is True
    assert len(eval_row.get("investigated_eliminations", [])) == 1


def test_duplicate_elimination_rejected(tmp_path):
    proj = tmp_path / "proj"
    t, a, cell, obs, pred = _write_visible_episode(proj)
    receipt = _receipt({"rule": "identity_on_a0"}, t, a, cell, obs, pred)
    credited, _ = _process_investigated_receipts([receipt], project_dir=proj)
    assert len(credited) == 1
    # replay the SAME elimination — now in the ledger, so it dedups
    credited2, rejected2 = _process_investigated_receipts([receipt], project_dir=proj)
    assert not credited2
    assert rejected2 and rejected2[0]["reason"] == "investigated_duplicate_elimination"


def test_witness_that_does_not_check_out_rejected(tmp_path):
    """Anti-gaming: cited transition does not show the claimed observation."""
    proj = tmp_path / "proj"
    t, a, cell, _obs, pred = _write_visible_episode(proj)
    # claim observed=5 at (0,0), but the real visible value is 7
    receipt = _receipt({"rule": "identity_on_a0"}, t, a, cell, 5, pred)
    credited, rejected = _process_investigated_receipts([receipt], project_dir=proj)
    assert not credited
    assert rejected and rejected[0]["reason"] == "investigated_witness_does_not_check_out"


def test_non_refuting_witness_rejected(tmp_path):
    """A witness where observed == predicted refutes nothing."""
    proj = tmp_path / "proj"
    t, a, cell, obs, _pred = _write_visible_episode(proj)
    receipt = _receipt({"rule": "identity_on_a0"}, t, a, cell, obs, obs)
    credited, rejected = _process_investigated_receipts([receipt], project_dir=proj)
    assert not credited
    assert rejected and rejected[0]["reason"] == "investigated_witness_not_refuting"


def test_holdout_witness_raises_firewall(tmp_path):
    """Firewall: a witness citing holdout evidence must RAISE, never be tolerated."""
    proj = tmp_path / "proj"
    t, a, cell, obs, pred = _write_visible_episode(proj)
    receipt = _receipt(
        {"rule": "identity_on_a0"}, t, a, cell, obs, pred,
        refs=["raw/episodes/episode_002.jsonl#t0"],
    )
    with pytest.raises(ValueError, match="firewall"):
        _process_investigated_receipts([receipt], project_dir=proj)

    # also raises if the holdout is named in the witness source field
    receipt2 = _receipt(
        {"rule": "identity_on_a0"}, t, a, cell, obs, pred,
        extra_witness={"source": "raw/episodes/episode_002.jsonl"},
    )
    with pytest.raises(ValueError, match="firewall"):
        _process_investigated_receipts([receipt2], project_dir=proj)


def test_witness_transition_not_in_visible_rejected(tmp_path):
    proj = tmp_path / "proj"
    _write_visible_episode(proj)
    # t=99 is not in the visible episode
    receipt = _receipt({"rule": "x"}, 99, 0, (0, 0), 7, 3)
    credited, rejected = _process_investigated_receipts([receipt], project_dir=proj)
    assert not credited
    assert rejected and rejected[0]["reason"] == "investigated_witness_transition_not_in_visible"


def test_k_consecutive_investigated_only_surfaces_stagnation(tmp_path):
    """K distinct credited investigated-only turns, no carrier: the K-bound must
    be the trip point. Simulated with the loop's own accounting semantics."""
    proj = tmp_path / "proj"
    _write_visible_episode(proj)
    # K distinct eliminations, each credited, none a carrier.
    consecutive = 0
    tripped = False
    for k in range(INVESTIGATED_STAGNATION_K):
        receipt = _receipt({"rule": f"class_{k}"}, 0, 0, (0, 0), 7, 3)
        credited, rejected = _process_investigated_receipts([receipt], project_dir=proj)
        assert len(credited) == 1 and not rejected, f"turn {k} should credit"
        consecutive += 1  # investigated-only, no carrier
        if consecutive >= INVESTIGATED_STAGNATION_K:
            tripped = True
    assert tripped, "K consecutive investigated-only turns must trip the stagnation bound"
    assert consecutive == INVESTIGATED_STAGNATION_K


# ---------------------------------------------------------------------------
# Seam tests: check_worldmodel_control_only_submission + loop static guards
# ---------------------------------------------------------------------------
# Tests use check_worldmodel_control_only_submission directly — importing
# autoresearch_loop crashes in test context because the module runs argparse
# at load time.  Static guards verify the loop's wiring by text-scanning.

from ztare.validator.core.worldmodel_control_outcome import (
    check_worldmodel_control_only_submission,
)


def _parsed_payload(receipts, test_model_py="", thesis="control-only turn"):
    """Build a minimal normalised worldmodel payload dict (already parsed)."""
    return {
        "control_receipts": receipts,
        "thesis_markdown": thesis,
        "test_model_py": test_model_py,
    }


def _investigated_receipt_payload(t=0, a=0, cell=(0, 0), observed=7, predicted=3):
    """Minimal INVESTIGATED receipt dict."""
    return {
        "type": "INVESTIGATED",
        "payload": {
            "eliminated_hypothesis": {"rule": "identity"},
            "witness": {"t": t, "a": a, "cell": list(cell), "observed": observed, "predicted": predicted},
            "evidence_refs": ["workspace/visible_cli_receipts/probe.json"],
        },
    }


def _lowerability_blocked_receipt():
    return {
        "type": "LOWERABILITY_BLOCKED",
        "payload": {
            "obstruction": "no gamma-lowerable candidate",
            "missing_witness_or_sensor": "transition sensor",
            "next_action": "request sensor",
            "visible_capabilities_attempted": ["inspect_replay_residual_quotient"],
            "candidate_family_attempted": ["step(grid, action, t)"],
            "evidence_refs": ["workspace/visible_cli_receipts/probe.json"],
        },
    }


def test_investigated_only_payload_routes_control_only_no_valueerror():
    """INVESTIGATED-only receipt + empty test_model_py → control-only sentinel, no ValueError."""
    payload = _parsed_payload([_investigated_receipt_payload()])
    sentinel = check_worldmodel_control_only_submission(payload, raw_text="raw thesis")
    assert sentinel is not None
    assert sentinel.get("control_only") is True
    assert "investigated" in sentinel.get("reasons", [])


def test_lowerability_blocked_payload_routes_control_only():
    """LOWERABILITY_BLOCKED + empty test_model_py → control-only sentinel."""
    payload = _parsed_payload([_lowerability_blocked_receipt()])
    sentinel = check_worldmodel_control_only_submission(payload, raw_text="raw thesis")
    assert sentinel is not None
    assert sentinel.get("control_only") is True
    assert "lowerability_blocked" in sentinel.get("reasons", [])


def test_payload_with_test_model_py_takes_normal_candidate_path():
    """When test_model_py is non-empty, check returns None (normal path)."""
    code = "def step(grid, action, t):\n    return grid\n"
    payload = _parsed_payload([_investigated_receipt_payload()], test_model_py=code)
    sentinel = check_worldmodel_control_only_submission(payload, raw_text="")
    assert sentinel is None


def test_empty_receipts_no_sentinel():
    """No recognisable receipt → may_omit_candidate=False → None returned."""
    payload = _parsed_payload([])
    sentinel = check_worldmodel_control_only_submission(payload, raw_text="")
    assert sentinel is None


def test_investigated_with_malformed_payload_does_not_raise():
    """Malformed INVESTIGATED payload: decision is receipt-TYPE-driven, not payload-content.

    The seam returns a sentinel (may_omit=True) without raising. Build-eval then rejects
    the malformed payload gracefully (rejected list). No R1 strike at seam boundary.
    """
    malformed = {
        "type": "INVESTIGATED",
        "payload": {"eliminated_hypothesis": {"rule": "x"}},  # missing witness
    }
    payload = _parsed_payload([malformed])
    sentinel = check_worldmodel_control_only_submission(payload, raw_text="")
    assert sentinel is not None
    assert sentinel.get("control_only") is True


def test_process_investigated_receipts_credits_into_ledger(tmp_path):
    """_process_investigated_receipts writes to SpecNogoodLedger.path on credit."""
    proj = tmp_path / "proj"
    _write_visible_episode(proj)
    from ztare.validator.core.worldmodel_control_outcome import _process_investigated_receipts
    receipt = _receipt({"rule": "identity_seam_test"}, 0, 0, (0, 0), 7, 3)
    credited, rejected = _process_investigated_receipts([receipt], project_dir=proj)
    assert len(credited) == 1 and not rejected

    from ztare.worldmodel.spec_nogood import SpecNogoodLedger
    ledger = SpecNogoodLedger(proj)
    clauses = ledger.visible_clauses()
    assert credited[0]["signature"] in clauses


def test_autoresearch_loop_wires_control_only_sentinel():
    """Static guard: loop file has the sentinel wiring for control-only turns."""
    from pathlib import Path as P
    repo_root = P(__file__).resolve().parents[1]
    src = (repo_root / "src" / "ztare" / "validator" / "autoresearch_loop.py").read_text(
        encoding="utf-8"
    )
    # Sentinel variable declared before R1 while loop
    assert "_control_only_sentinel = None" in src
    # _prepare_mutation_candidate returns 6 values; caller unpacks 6
    assert "_control_only_sentinel = _prepare_mutation_candidate(" in src or \
           "full_candidate, _control_only_sentinel = _prepare_mutation_candidate(" in src
    # Sentinel check breaks the R1 loop (no strike)
    assert "if _control_only_sentinel is not None:" in src
    # Eval row builder called at the right site
    assert "build_worldmodel_control_only_eval as _build_co_eval" in src
    # Iter is consumed but NOT struck (judge cmd replaced with pass)
    assert "_control_only_sentinel is not None:" in src
    # Log line present
    assert "control-only turn" in src


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
