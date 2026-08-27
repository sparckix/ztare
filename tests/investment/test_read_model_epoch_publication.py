import json
from pathlib import Path
import csv

from ztare.investment import workspace


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_read_model_stays_on_last_completed_composite_epoch(
    tmp_path: Path, monkeypatch,
) -> None:
    cached = {
        "schema": workspace.READ_MODEL_SCHEMA,
        "workspace_path": str(tmp_path),
        "discovery": {"latest_run": {"run_sha256": "stable-discovery"}},
        "capital_authority": False,
    }
    _write(tmp_path / "state/read_model.json", cached)
    _write(
        tmp_path / "discovery/latest.json",
        {"run_sha256": "unpublished-discovery", "source_run_sha256": "old-source"},
    )
    monkeypatch.setattr(
        workspace, "_current_source_run", lambda _root: {"run_sha256": "new-source"},
    )
    monkeypatch.setattr(
        workspace, "_build_read_model_unlocked",
        lambda _root: (_ for _ in ()).throw(AssertionError("mixed epoch rebuilt")),
    )

    assert workspace.build_read_model(tmp_path) == cached
    assert (
        workspace.read_cached_read_model(tmp_path)["discovery"]["latest_run"]["run_sha256"]
        == "stable-discovery"
    )


def test_household_goal_surface_reuses_point_in_time_fx_outside_latest_run(
    tmp_path: Path, monkeypatch,
) -> None:
    observations = tmp_path / "data" / "observations.csv"
    observations.parent.mkdir(parents=True)
    with observations.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=(
            "entity_id", "metric_id", "value", "observed_at", "available_at",
            "observation_id", "source_ref",
        ))
        writer.writeheader()
        writer.writerow({
            "entity_id": "EURUSD", "metric_id": "usd_per_eur", "value": "1.17",
            "observed_at": "2026-08-20T00:00:00Z",
            "available_at": "2026-08-20T00:00:00Z",
            "observation_id": "fx:eurusd", "source_ref": "fred:eurusd",
        })
        writer.writerow({
            "entity_id": "EURUSD", "metric_id": "usd_per_eur", "value": "9.99",
            "observed_at": "2026-08-22T00:00:00Z",
            "available_at": "2026-08-22T00:00:00Z",
            "observation_id": "fx:future", "source_ref": "fred:future",
        })
    monkeypatch.setattr(
        workspace, "_current_source_run",
        lambda _root: {"as_of": "2026-08-21T00:00:00Z"},
    )
    captured = {}
    monkeypatch.setattr(
        workspace, "compile_private_household_workspace",
        lambda path, **kwargs: captured.update({"path": path, **kwargs}) or {"ok": True},
    )

    assert workspace._current_household_goal_surface(
        tmp_path,
        {"household_intake": "household/intake.yaml", "household_base_currency": "USD"},
        as_of="2026-08-21T00:00:00Z",
    ) == {"ok": True}
    assert captured["fx_to_base"] == {"EUR": 1.17}
    assert captured["fx_source_refs"] == ("fred:eurusd",)


def test_read_model_reuses_the_last_instrument_admission_epoch(tmp_path: Path) -> None:
    body = {
        "schema": workspace.WORKSPACE_INSTRUMENT_PORTFOLIO_ADMISSIONS_SCHEMA,
        "compiled_at": "2026-08-20T12:00:00Z",
        "admissions": [],
        "capital_authority": False,
    }
    expected = {
        **body,
        "workspace_admissions_sha256": workspace.stable_sha256(body),
    }
    _write(tmp_path / "portfolio/instrument_admissions/latest.json", expected)

    assert workspace._current_instrument_portfolio_admissions(tmp_path) == expected
