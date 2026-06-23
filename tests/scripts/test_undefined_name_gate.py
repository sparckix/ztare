from __future__ import annotations

import importlib.util
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/public/control/undefined_name_gate.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("undefined_name_gate", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_undefined_name_gate_fails_on_f821(tmp_path: Path, capsys) -> None:
    gate = _load_gate()
    (tmp_path / "bad.py").write_text("def f():\n    return missing_name\n", encoding="utf-8")

    rc = gate.main(["--label", "fixture", str(tmp_path)])

    out = capsys.readouterr()
    assert rc == 1
    assert "undefined name 'missing_name'" in out.out
    assert "F821 undefined-name" in out.err


def test_undefined_name_gate_passes_after_pyflakes_runs(tmp_path: Path, capsys) -> None:
    gate = _load_gate()
    (tmp_path / "good.py").write_text("def f():\n    return 1\n", encoding="utf-8")

    rc = gate.main(["--label", "fixture", str(tmp_path)])

    out = capsys.readouterr()
    assert rc == 0
    assert "fixture: 0 undefined names; pyflakes import+scan verified" in out.out
