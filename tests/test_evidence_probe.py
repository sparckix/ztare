"""Planted tests for the governed evidence probe (observation sort)."""

import json

from ztare.common.operator_proposal_contract import write_proposal_cards
from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.evidence_probe import (
    PAYLOAD_CHAR_CAP,
    RECEIPT_SCHEMA,
    run_evidence_probe,
)
from ztare.worldmodel.experiment_executor import execute_experiments


COUNT_PROBE = (
    "def probe(episodes):\n"
    "    return {name: {'transitions': len(rows),\n"
    "                   'distinct_t': len({row['t'] for row in rows})}\n"
    "            for name, rows in sorted(episodes.items())}\n"
)


def _project(tmp_path, *, run_role=None):
    proj = tmp_path / "proj"
    (proj / "workspace").mkdir(parents=True)
    g0 = ((1, 0), (0, 0))
    g1 = ((0, 1), (0, 0))
    visible = EpisodeLog()
    visible.append(g0, 1, g1)  # t=0
    visible.append(g1, 2, g0)  # t=1
    visible.write_jsonl(proj / "raw" / "episodes" / "episode_001.jsonl")
    holdout = EpisodeLog()
    holdout.append(g0, 3, g0)  # t=0
    holdout.write_jsonl(proj / "raw" / "episodes" / "episode_002.jsonl")
    if run_role is not None:
        (proj / "MANIFEST.json").write_text(json.dumps({"run_role": run_role}))
    return proj


def _card(plan, kind="evidence_probe"):
    return {
        "schema": "strategy-experiment-v1",
        "failure_family": f"{kind}|{json.dumps(plan, sort_keys=True)}",
        "kind": kind,
        "rationale": "planted",
        "falsifiable_prediction": "planted",
        "action_plan": plan,
        "kill_condition": "never-matching-kill-condition",
        "disposition": "open",
    }


def test_happy_path_counts_transitions(tmp_path):
    receipt = run_evidence_probe(_project(tmp_path), COUNT_PROBE)
    assert receipt["schema"] == RECEIPT_SCHEMA
    assert receipt["status"] == "ok"
    # No MANIFEST run_role → fail closed to EVALUATION: holdout stays sealed.
    assert receipt["payload"] == {"visible": {"transitions": 2, "distinct_t": 2}}
    assert len(receipt["probe_sha"]) == 64
    assert "payload_truncated" not in receipt


_KEYS_PROBE = "def probe(episodes):\n    return {'keys': sorted(episodes.keys())}\n"


def test_evaluation_seals_holdout_from_a_probe(tmp_path):
    receipt = run_evidence_probe(_project(tmp_path, run_role="EVALUATION"), _KEYS_PROBE)
    assert receipt["status"] == "ok"
    assert receipt["payload"] == {"keys": ["visible"]}


def test_missing_run_role_fails_closed_to_evaluation(tmp_path):
    receipt = run_evidence_probe(_project(tmp_path), _KEYS_PROBE)
    assert receipt["status"] == "ok"
    assert receipt["payload"] == {"keys": ["visible"]}


def test_discovery_exposes_holdout_to_a_probe(tmp_path):
    receipt = run_evidence_probe(_project(tmp_path, run_role="DISCOVERY"), _KEYS_PROBE)
    assert receipt["status"] == "ok"
    assert receipt["payload"] == {"keys": ["holdout", "visible"]}


def test_purity_rejection_names_the_marker(tmp_path):
    src = "def probe(episodes):\n    return {'x': open('/etc/passwd').read()}\n"
    receipt = run_evidence_probe(_project(tmp_path), src)
    assert receipt["status"] == "error"
    assert "open" in receipt["error"]


def test_allowlist_blocks_import_escapes(tmp_path):
    proj = _project(tmp_path)
    for bad in (
        "import os\ndef probe(e):\n    return {'x': os.getpid()}\n",
        "import urllib.request\ndef probe(e):\n    return {}\n",
        "def probe(e):\n    return {'x': __import__('os').getpid()}\n",
        "def probe(e):\n    return {'x': ().__class__.__bases__}\n",
    ):
        receipt = run_evidence_probe(proj, bad)
        assert receipt["status"] == "error", bad


def test_quotient_import_is_whitelisted_but_other_ztare_imports_are_not(tmp_path):
    ok_src = (
        "from ztare.worldmodel.evidence_quotients import event_timeline, episode_contrast\n"
        "def probe(episodes):\n"
        "    return {'quotients': [callable(event_timeline), callable(episode_contrast)]}\n"
    )
    proj = _project(tmp_path)
    receipt = run_evidence_probe(proj, ok_src)
    assert receipt["status"] == "ok"
    assert receipt["payload"] == {"quotients": [True, True]}

    bad_src = "import ztare.worldmodel.harness\ndef probe(episodes):\n    return {}\n"
    rejected = run_evidence_probe(proj, bad_src)
    assert rejected["status"] == "error"
    assert "not allowed" in rejected["error"]


def test_timeout_is_a_loud_error_receipt(tmp_path):
    src = "def probe(episodes):\n    while True:\n        pass\n"
    receipt = run_evidence_probe(_project(tmp_path), src, timeout_seconds=1)
    assert receipt["status"] == "error"
    assert "timed out" in receipt["error"]


def test_empty_stdout_is_a_loud_error_receipt(tmp_path):
    # exits 0 before the runner prints, without a forbidden import
    src = "raise SystemExit(0)\ndef probe(episodes):\n    return {}\n"
    receipt = run_evidence_probe(_project(tmp_path), src)
    assert receipt["status"] == "error"
    assert "empty stdout" in receipt["error"]


def test_probe_exception_surfaces_stderr_prefix(tmp_path):
    src = "def probe(episodes):\n    raise ValueError('planted probe failure')\n"
    receipt = run_evidence_probe(_project(tmp_path), src)
    assert receipt["status"] == "error"
    assert "planted probe failure" in receipt["error"]


def test_oversized_payload_truncates_loudly(tmp_path):
    src = "def probe(episodes):\n    return {'blob': 'x' * 30000}\n"
    receipt = run_evidence_probe(_project(tmp_path), src)
    assert receipt["status"] == "ok"
    assert isinstance(receipt["payload"], str)
    assert len(receipt["payload"]) == PAYLOAD_CHAR_CAP
    assert "dropped" in receipt["payload_truncated"]


def test_executor_dispatches_probe_source_to_observed(tmp_path):
    proj = _project(tmp_path)
    ledger = proj / "workspace" / "strategy_experiments.jsonl"
    assert write_proposal_cards(ledger, [_card({"probe_source": COUNT_PROBE})])

    result = execute_experiments(proj, all_open=True)

    assert result["processed"] == 1
    receipt = result["receipts"][0]
    assert receipt["disposition"] == "observed"
    assert "evidence probe observed" in receipt["outcome_summary"]
    assert '"transitions": 2' in receipt["outcome_summary"]
    rows = result["probe_rows"]
    assert rows[0]["kind"] == "evidence_probe"
    assert rows[0]["status"] == "observed"
    assert rows[0]["receipt"]["schema"] == RECEIPT_SCHEMA


def test_executor_blocks_impure_probe_with_error_receipt(tmp_path):
    proj = _project(tmp_path)
    ledger = proj / "workspace" / "strategy_experiments.jsonl"
    src = "def probe(episodes):\n    return {'x': open('secret').read()}\n"
    assert write_proposal_cards(ledger, [_card({"probe_source": src})])

    result = execute_experiments(proj, all_open=True)

    receipt = result["receipts"][0]
    assert receipt["disposition"] == "blocked"
    assert "open" in receipt["outcome_summary"]


def test_carrier_fields_win_over_probe_source(tmp_path):
    # Documented choice: a card carrying BOTH carrier fields and probe_source
    # routes to the carrier probe (law sort outranks observation sort). Here
    # the carrier is unresolvable, so the receipt is a loud carrier block —
    # never a silent observation.
    proj = _project(tmp_path)
    ledger = proj / "workspace" / "strategy_experiments.jsonl"
    plan = {
        "probe_source": COUNT_PROBE,
        "repair_carrier": "workspace/does_not_exist.py",
        "target_residual_class": "planted_residual",
    }
    assert write_proposal_cards(ledger, [_card(plan, kind="carrier_repair_probe")])

    result = execute_experiments(proj, all_open=True)

    receipt = result["receipts"][0]
    assert receipt["disposition"] == "blocked"
    assert "carrier not runnable" in receipt["outcome_summary"]
