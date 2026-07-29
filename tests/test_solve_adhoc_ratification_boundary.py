import importlib.util
import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts/public/control/leanmill/solve_adhoc.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "solve_adhoc_ratification_boundary_test", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_proof_bearing_definition_returns_typed_unsupported_result(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    module = load_module()
    source = tmp_path / "Construction.lean"
    source.write_text(
        "namespace Construction\n\n"
        "def witness (n : Nat) : Nat := n\n\n"
        "end Construction\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        module,
        "_ratify_carried_theorem",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("an unsupported construction must not enter theorem solving")
        ),
    )

    rc = module.main([
        "--target",
        "Construction.witness",
        "--source-file",
        str(source),
        "--ratify-existing-target",
        "--json",
    ])

    assert rc == 0
    result = json.loads(capsys.readouterr().out)
    assert result["schema"] == "leanmill.ratification_boundary.v1"
    assert result["outcome"] == "unsupported_artifact_kind"
    assert result["attempted"] == 0
    assert result["closure_certificate"] is None
    assert result["theorem_contract_applied"] is False
    assert result["results"] == [{
        "target_name": "Construction.witness",
        "outcome": "unsupported_artifact_kind",
        "artifact_class": "construction_artifact",
        "declaration_kind": "def",
        "provider": None,
        "providers_tried": [],
        "compile_ok": None,
        "reason": (
            "construction artifacts require a typed construction-artifact ratification contract; "
            "the theorem conclusion-perturbation contract was not applied"
        ),
        "required_next_capability": "construction_artifact_ratification",
    }]


def test_theorem_ratification_still_enters_preverified_theorem_contract(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    module = load_module()
    source = tmp_path / "Theorem.lean"
    source.write_text(
        "namespace TheoremRoute\n\n"
        "theorem target : True := by trivial\n\n"
        "end TheoremRoute\n",
        encoding="utf-8",
    )
    captured = {}

    def fake_ratify(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return {"outcome": "closed"}

    monkeypatch.setattr(module, "_ratify_carried_theorem", fake_ratify)
    rc = module.main([
        "--target",
        "TheoremRoute.target",
        "--source-file",
        str(source),
        "--ratify-existing-target",
        "--json",
    ])

    assert rc == 0
    assert json.loads(capsys.readouterr().out) == {"outcome": "closed"}
    assert captured["args"][0] == "TheoremRoute.target"
    assert "sorry" in captured["args"][1]
    assert captured["args"][2] == "by trivial"
    assert captured["kwargs"]["provider_label"] == "existing_artifact"


def test_loading_ratification_cli_does_not_import_proof_search() -> None:
    code = f"""
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location('ratification_cli_probe', {str(SCRIPT)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(json.dumps(sorted(name for name in sys.modules if name == 'ztare.leanmill.solver.solver_core')))
"""
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
        env={**__import__("os").environ, "PYTHONPATH": "src"},
    )
    assert json.loads(completed.stdout) == []
