import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "ns_gate_check.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("ns_gate_check", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _rubric():
    return {
        "potential_function": {
            "name": "score",
            "field": "score",
            "ceiling": 100,
            "monotone": "increasing",
            "tolerance": 0.0,
        },
        "bound_chain": [
            {
                "id": "declared_bound",
                "premises": ["fixed topology"],
                "conclusion": "payoff <= price",
                "constants": {"C": 1.0},
                "scope": "fixed test topology",
                "depends_on": [],
            }
        ],
        "special_case_candidates": [
            {
                "name": "narrow case",
                "structural_barrier_addressed": "test barrier",
                "instantiation_hint": "test setup",
                "complexity_class": "narrower",
            }
        ],
        "no_auxiliary_object": True,
    }


def test_ns_gate_check_accepts_json_history(tmp_path: Path, capsys):
    module = _load_script()
    history = tmp_path / "history.json"
    rubric = tmp_path / "rubric.json"
    history.write_text(json.dumps([{"score": 10}, {"score": 20}, {"score": 30}]), encoding="utf-8")
    rubric.write_text(json.dumps(_rubric()), encoding="utf-8")

    rc = module.main(["--iteration-history", str(history), "--rubric", str(rubric)])

    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["n_iterations"] == 3
    assert set(payload["gates"]) == {
        "potential_function_monotonicity",
        "bound_chain_consistency",
        "stagnation_special_case_hint",
        "auxiliary_object_declaration",
        "limit_passage_inheritance_lemma",
        "threshold_dichotomy_branch_coverage",
    }
    assert payload["promote_blocked"] is False
    assert payload["gates"]["threshold_dichotomy_branch_coverage"]["semantics"] == "advisory"


def test_ns_gate_check_accepts_jsonl_history(tmp_path: Path, capsys):
    module = _load_script()
    history = tmp_path / "history.jsonl"
    rubric = tmp_path / "rubric.json"
    rows = [{"score": 10}, {"score": 20}, {"score": 30}, {"score": 40}]
    history.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    rubric.write_text(json.dumps(_rubric()), encoding="utf-8")

    rc = module.main(["--iteration-history", str(history), "--rubric", str(rubric)])

    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["n_iterations"] == 4
    assert payload["advisory_fired"] is False
    assert payload["gates"]["threshold_dichotomy_branch_coverage"]["result"]["passed"] is True


def test_ns_gate_check_threshold_dichotomy_can_block_when_enforced(tmp_path: Path, capsys):
    module = _load_script()
    history = tmp_path / "history.json"
    rubric = tmp_path / "rubric.json"
    bad_rubric = _rubric()
    bad_rubric.update({
        "enforce_threshold_dichotomy_branch_coverage": True,
        "threshold_dichotomies": [
            {
                "name": "survival_wall",
                "threshold_T": 2 / 3,
                "degeneracy_D": "null/no-survivor route",
                "branch_proofs": {
                    "exceeds_threshold_proof": "ZtareProofs/ns_leray_gain_tax_trackb_obligation.lean",
                },
            }
        ],
    })
    history.write_text(json.dumps([{"score": 10}, {"score": 20}]), encoding="utf-8")
    rubric.write_text(json.dumps(bad_rubric), encoding="utf-8")

    rc = module.main(["--iteration-history", str(history), "--rubric", str(rubric)])

    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload["promote_blocked"] is True
    gate = payload["gates"]["threshold_dichotomy_branch_coverage"]
    assert gate["semantics"] == "promote_blocking"
    assert gate["result"]["passed"] is False
    assert gate["result"]["violations"][0]["type"] == "missing_branch_proof"


def test_ns_gate_check_limit_passage_can_block_when_enforced(tmp_path: Path, capsys):
    module = _load_script()
    history = tmp_path / "history.json"
    rubric = tmp_path / "rubric.json"
    bad_rubric = _rubric()
    bad_rubric.update({
        "enforce_limit_passage_inheritance_lemma": True,
        "finite_prefix_results": True,
        "limit_passage_steps": [
            {
                "name": "finite_prefix_to_profile_limit",
                "sequence_described": "LP prefix receipts S_N",
                "inheritance_lemma": "",
                "property_inherited": "positive prefix price",
            }
        ],
    })
    history.write_text(json.dumps([{"score": 10}, {"score": 20}]), encoding="utf-8")
    rubric.write_text(json.dumps(bad_rubric), encoding="utf-8")

    rc = module.main(["--iteration-history", str(history), "--rubric", str(rubric)])

    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload["promote_blocked"] is True
    gate = payload["gates"]["limit_passage_inheritance_lemma"]
    assert gate["semantics"] == "promote_blocking"
    assert gate["result"]["passed"] is False
    assert gate["result"]["violations"][0]["type"] == "step_incomplete"


def test_ns_gate_check_auxiliary_object_can_block_when_enforced(tmp_path: Path, capsys):
    module = _load_script()
    history = tmp_path / "history.json"
    rubric = tmp_path / "rubric.json"
    bad_rubric = _rubric()
    bad_rubric.pop("no_auxiliary_object")
    bad_rubric.update({"enforce_auxiliary_object_declaration": True})
    history.write_text(json.dumps([{"score": 10}, {"score": 20}]), encoding="utf-8")
    rubric.write_text(json.dumps(bad_rubric), encoding="utf-8")

    rc = module.main(["--iteration-history", str(history), "--rubric", str(rubric)])

    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload["promote_blocked"] is True
    gate = payload["gates"]["auxiliary_object_declaration"]
    assert gate["semantics"] == "promote_blocking"
    assert gate["result"]["passed"] is False
    assert gate["result"]["violations"][0]["type"] == "auxiliary_object_not_declared"
