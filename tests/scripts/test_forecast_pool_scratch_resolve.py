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


def test_tail_insurance_premium_help_matches_probability_validator(tmp_path: Path) -> None:
    for command in ("add-forecast", "scratch-forecast"):
        help_result = run_cli(tmp_path, command, "--help", check=False)
        assert help_result.returncode == 0
        assert "F8 legacy probability-like magnitude in [0,1]" in help_result.stdout
        assert "F8 legacy magnitude (1-100)" not in help_result.stdout


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


def test_scratch_forecast_bid_ask_spread_is_ask_minus_bid(tmp_path: Path) -> None:
    forecast = run_cli(
        tmp_path,
        "scratch-forecast",
        "--owner", "deepseek_forecaster",
        "--domain", "forecast_calibration",
        "--task-type", "micro_contract",
        "--question", "Will the bid ask convention stay non-negative?",
        "--p-success", "0.50",
        "--expected-cost-agent-minutes", "1",
        "--tail-insurance-premium", "0.2",
        "--tail-loss-magnitude", "0.5",
        "--p-buy-yes-max", "0.42",
        "--p-sell-yes-min", "0.72",
        "--failure-modes-json", "{}",
        "--rationale-short", "Bid ask convention regression.",
        "--resolution-predicate", "TRUE iff spread convention is ask minus bid.",
        "--no-prediction-ledger",
        "--ack-uncertified",
    )
    scratch = json.loads(Path(json.loads(forecast.stdout)["path"]).read_text())
    assert scratch["p_buy_yes_max"] == 0.42
    assert scratch["p_sell_yes_min"] == 0.72
    assert scratch["spread"] == 0.30

    reversed_quote = run_cli(
        tmp_path,
        "scratch-forecast",
        "--owner", "deepseek_forecaster",
        "--domain", "forecast_calibration",
        "--task-type", "micro_contract",
        "--question", "Will reversed bid ask quotes be rejected?",
        "--p-success", "0.50",
        "--expected-cost-agent-minutes", "1",
        "--tail-insurance-premium", "0.2",
        "--tail-loss-magnitude", "0.5",
        "--p-buy-yes-max", "0.72",
        "--p-sell-yes-min", "0.42",
        "--failure-modes-json", "{}",
        "--rationale-short", "Bid ask convention regression.",
        "--resolution-predicate", "TRUE iff reversed quotes fail.",
        "--no-prediction-ledger",
        "--ack-uncertified",
        check=False,
    )
    assert reversed_quote.returncode != 0
    assert "--p-buy-yes-max must be <= --p-sell-yes-min" in reversed_quote.stderr


def test_aggregate_exposes_confident_no_adjusted_view(tmp_path: Path) -> None:
    contract_id = "confident_no_adjustment_smoke"
    run_cli(
        tmp_path,
        "init-contract",
        "--contract-id", contract_id,
        "--layer", "micro",
        "--task-type", "forecast_calibration",
        "--question", "Will aggregate expose the confident-NO adjusted view?",
        "--objective-resolver", "unit_test",
        "--success-threshold", "json fields present",
        "--horizon", "immediate",
        "--value-if-success", "1",
        "--cost-penalty", "0",
        "--risk-penalty", "0",
    )
    for agent_id, p_success in (("codex_low_a", "0.04"), ("codex_low_b", "0.08")):
        run_cli(
            tmp_path,
            "add-forecast",
            "--contract-id", contract_id,
            "--agent-id", agent_id,
            "--domain", "forecast_calibration",
            "--p-success", p_success,
            "--expected-cost-agent-minutes", "1",
            "--failure-modes-json", "{}",
            "--rationale-short", "Confident NO adjustment regression.",
            "--read-only-attestation",
        )

    aggregate = json.loads(run_cli(tmp_path, "aggregate", "--contract-id", contract_id).stdout)
    raw_p = aggregate["aggregate"]["p_success"]
    adjusted_p = aggregate["aggregate"]["confident_no_adjusted_p_success"]

    assert raw_p < 0.10
    assert adjusted_p > raw_p
    assert aggregate["aggregate"]["raw_mean_panel_p_success"] == 0.06
    assert adjusted_p == 0.355
    assert aggregate["aggregate"]["confident_no_adjusted_weighted_logit_p_success"] > raw_p
    assert aggregate["aggregate"]["confident_no_adjusted_forecast_count"] == 2
    policy = aggregate["aggregate"]["confident_no_adjustment_policy"]
    assert policy["policy_id"] == "F100_confident_no_discount_v1"
    assert "time-valid labels/baselines" in policy["scope"]
    assert "FRED current-label rows are excluded" in policy["latest_scope_caveat"]
    assert "bulk repair/rescore" in policy["latest_scope_caveat"]
    assert all(row["confident_no_adjustment_applied"] for row in aggregate["participants"])
