import json
import os
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/public/control/forecast/pool.py"


def run_cli(tmp_path: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["FORECAST_POOL_ROOT"] = str(tmp_path / "forecast_pool")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    return result


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_scratch_resolve_updates_artifact_and_prediction_ledger(tmp_path: Path) -> None:
    ledger = tmp_path / "prediction_ledger.jsonl"
    forecast = run_cli(
        tmp_path,
        "scratch-forecast",
        "--owner", "codex:RD",
        "--domain", "ns_route1",
        "--task-type", "meso_contract",
        "--question", "Will the scratch resolver close its local mirror?",
        "--p-success", "0.42",
        "--expected-cost-agent-minutes", "3",
        "--tail-insurance-premium", "0.31",
        "--tail-loss-magnitude", "0.7",
        "--failure-modes-json", "{\"schema_regression\": 1.0}",
        "--rationale-short", "Regression test scratch forecast.",
        "--resolution-predicate", "TRUE iff scratch-resolve updates both files.",
        "--prediction-ledger", str(ledger),
        "--ack-uncertified",
    )
    forecast_payload = json.loads(forecast.stdout)
    prediction_id = forecast_payload["prediction_id"]
    scratch_path = Path(forecast_payload["path"])
    assert scratch_path.is_absolute()
    scratch = json.loads(scratch_path.read_text())
    assert scratch["prediction_id"] == prediction_id

    resolved = run_cli(
        tmp_path,
        "scratch-resolve",
        "--prediction-id", prediction_id,
        "--actual-outcome", "TRUE",
        "--actual-outcome-bucket", "success",
        "--resolution-summary", "scratch resolver updated both artifacts",
        "--prediction-ledger", str(ledger),
    )
    resolved_payload = json.loads(resolved.stdout)
    assert resolved_payload["updated_prediction_rows"] == 1

    scratch = json.loads(scratch_path.read_text())
    assert scratch["actual_outcome"] == "TRUE"
    assert scratch["actual_outcome_bucket"] == "success"
    assert scratch["resolution"]["resolution_source"] == "forecast_pool scratch-resolve"

    rows = read_jsonl(ledger)
    assert len(rows) == 1
    assert rows[0]["prediction_id"] == prediction_id
    assert rows[0]["actual_outcome"] == "TRUE"
    assert rows[0]["actual_outcome_bucket"] == "success"
    assert rows[0]["resolution_source"] == "forecast_pool scratch-resolve"

    duplicate = run_cli(
        tmp_path,
        "scratch-resolve",
        "--prediction-id", prediction_id,
        "--actual-outcome", "TRUE",
        "--actual-outcome-bucket", "success",
        "--resolution-summary", "duplicate resolution should fail",
        "--prediction-ledger", str(ledger),
        check=False,
    )
    assert duplicate.returncode != 0
    assert "already has a resolution" in duplicate.stderr


def test_scratch_resolve_can_use_path_for_unmirrored_scratch(tmp_path: Path) -> None:
    ledger = tmp_path / "prediction_ledger.jsonl"
    forecast = run_cli(
        tmp_path,
        "scratch-forecast",
        "--owner", "codex_forecaster",
        "--domain", "ns_route1",
        "--task-type", "micro_contract",
        "--question", "Will path-only scratch resolution work?",
        "--p-success", "0.5",
        "--expected-cost-agent-minutes", "1",
        "--tail-insurance-premium", "0.2",
        "--tail-loss-magnitude", "0.5",
        "--failure-modes-json", "{}",
        "--rationale-short", "Path-only scratch forecast.",
        "--no-prediction-ledger",
        "--prediction-ledger", str(ledger),
        "--ack-uncertified",
    )
    forecast_payload = json.loads(forecast.stdout)
    assert forecast_payload["prediction_id"] is None

    resolved = run_cli(
        tmp_path,
        "scratch-resolve",
        "--scratch-path", forecast_payload["path"],
        "--actual-outcome", "FALSE",
        "--actual-outcome-bucket", "blocked",
        "--resolution-summary", "path-only scratch resolved without a ledger mirror",
        "--prediction-ledger", str(ledger),
    )
    resolved_payload = json.loads(resolved.stdout)
    assert resolved_payload["updated_prediction_rows"] == 0
    scratch = json.loads(Path(forecast_payload["path"]).read_text())
    assert scratch["actual_outcome"] == "FALSE"
    assert scratch["prediction_id"] is None
