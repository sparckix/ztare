"""Denotation-pinned-fraction rollup (factory read-model): counts + fraction + the no-applicable-rows None case.

The rollup is a pure REPORTER over the per-run `*.autoformalize_result.json` artifacts (the ONLY durable home of
`res["denotation"]`). It must count each 3-valued verdict, exclude NOT_APPLICABLE from the pinned-fraction
denominator, exclude null-denotation artifacts entirely (reporter never ran ≠ NOT_APPLICABLE), and shrug off
corrupt files. Runnable: `python tests/test_denotation_rollup.py`.
"""
import ast
import json
import os
import pathlib
import tempfile
from typing import Any

_SRC = pathlib.Path(__file__).resolve().parents[1] / "scripts/public/control/leanmill/factory_intelligence.py"


def _load_rollup():
    ns: dict = {"json": json, "os": os, "Path": pathlib.Path, "Any": Any}
    for node in ast.parse(_SRC.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.FunctionDef) and node.name == "denotation_rollup":
            exec(compile(ast.Module([node], []), "<f>", "exec"), ns)  # extract without importing the CLI module
    return ns["denotation_rollup"]


def _artifact(d: pathlib.Path, name: str, denotation) -> None:
    (d / f"{name}.autoformalize_result.json").write_text(
        json.dumps({"summary": "x", "denotation": denotation}), encoding="utf-8")


def test_counts_fraction_and_none_case():
    rollup = _load_rollup()
    with tempfile.TemporaryDirectory() as td:
        d = pathlib.Path(td)
        _artifact(d, "a", {"verdict": "PINNED", "reason": "anchor"})
        _artifact(d, "b", {"verdict": "PINNED", "reason": "composition"})
        _artifact(d, "c", {"verdict": "UNDERDETERMINED", "reason": "pending"})
        _artifact(d, "e", {"verdict": "REFUTED", "reason": "decoy"})
        _artifact(d, "f", {"verdict": "NOT_APPLICABLE", "reason": "no defs"})
        _artifact(d, "g", None)                                        # reporter never ran → excluded
        (d / "notes.json").write_text("{}", encoding="utf-8")          # wrong suffix → ignored
        (d / "bad.autoformalize_result.json").write_text("{corrupt", encoding="utf-8")  # unreadable → skipped
        (sub := d / "nested").mkdir()
        _artifact(sub, "h", {"verdict": "PINNED"})                     # recursion into subdirs

        r = rollup(roots=[d])
        assert r == {"pinned": 3, "underdetermined": 1, "refuted": 1, "not_applicable": 1,
                     "pinned_fraction": 3 / 5, "n_formalizations": 6}, r

    with tempfile.TemporaryDirectory() as td:                          # only NOT_APPLICABLE → fraction is None
        d = pathlib.Path(td)
        _artifact(d, "f", {"verdict": "NOT_APPLICABLE"})
        r = rollup(roots=[d])
        assert r["pinned_fraction"] is None and r["not_applicable"] == 1 and r["n_formalizations"] == 1, r

    with tempfile.TemporaryDirectory() as td:                          # empty store → zeros + None
        r = rollup(roots=[pathlib.Path(td)])
        assert r == {"pinned": 0, "underdetermined": 0, "refuted": 0, "not_applicable": 0,
                     "pinned_fraction": None, "n_formalizations": 0}, r
    print("OK: counts, pinned_fraction denominator, null/corrupt exclusion, None cases")


if __name__ == "__main__":
    test_counts_fraction_and_none_case()
