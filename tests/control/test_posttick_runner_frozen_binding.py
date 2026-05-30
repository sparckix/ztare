from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO / "scripts/public/control/posttick_runner.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "posttick_runner_under_test", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_start(store: Path, **overrides: object) -> None:
    ledger = store / "official" / "transitions.stamped.jsonl"
    ledger.parent.mkdir(parents=True)
    row = {
        "transition_type": "start_tick",
        "tick_id": "T",
        "forecast_contract_id": "C",
        "substrate": "frozen_substrate",
        "goal": "frozen goal",
    }
    row.update(overrides)
    ledger.write_text(json.dumps(row) + "\n", encoding="utf-8")


def test_posttick_rejects_substrate_that_differs_from_frozen_start(
    tmp_path, monkeypatch
) -> None:
    mod = load_module()
    store = tmp_path / "store"
    write_start(store)
    monkeypatch.setenv("ZTARE_OFFICIAL_STORE", str(store))

    err = mod._frozen_start_binding_error(
        tick_id="T",
        contract_id="C",
        substrate="wrong_substrate",
        goal="frozen goal",
    )

    assert err is not None
    assert "posttick substrate mismatch" in err


def test_posttick_accepts_byte_identical_frozen_fields(tmp_path, monkeypatch) -> None:
    mod = load_module()
    store = tmp_path / "store"
    write_start(store)
    monkeypatch.setenv("ZTARE_OFFICIAL_STORE", str(store))

    assert (
        mod._frozen_start_binding_error(
            tick_id="T",
            contract_id="C",
            substrate="frozen_substrate",
            goal="frozen goal",
        )
        is None
    )
