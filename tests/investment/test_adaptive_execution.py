import json
from dataclasses import replace

from ztare.common.execution_market import (
    ExecutionReceipt,
    ExecutionTask,
    ExecutorIdentity,
    plan_execution_market,
)
from ztare.investment.adaptive_execution import (
    _run_program_counterfactuals,
    verify_implied_growth_candidate,
)
from ztare.investment.valuation import solve_implied_growth


def _task() -> ExecutionTask:
    return ExecutionTask(
        task_id="X::implied-growth",
        task_family="jaggedthoughts.valuation.implied_growth",
        task_version="1",
        input_payload={
            "market_price": 100.0,
            "owner_earnings": 8.0,
            "discount_rate": 0.10,
            "terminal_growth": 0.025,
            "horizon_years": 10,
            "excess_net_cash": 0.0,
            "shares": 1.0,
        },
        evidence_sha256s=("a" * 64,),
        output_schema="implied-growth-v1",
        verifier_id="dcf-residual",
        verifier_version="1",
        verifier_kind="numeric",
        tolerance=1e-8,
        consequence_class="analytical-shadow",
        authority_ceiling="analytical_shadow",
        max_wallclock_s=60,
    )


def _executor(executor_id: str, mode: str, *, baseline: bool = False) -> ExecutorIdentity:
    return ExecutorIdentity(
        executor_id=executor_id,
        mode=mode,
        implementation_id=executor_id,
        implementation_sha256=("b" if baseline else "c") * 64,
        runtime="python" if baseline else "codex",
        model="none" if baseline else "account-default",
        reasoning_effort="none" if baseline else "high",
        capability_epoch="epoch-1",
        baseline=baseline,
        estimated_marginal_cost=0.0 if baseline else 1.0,
    )


def test_execution_market_promotes_only_after_same_epoch_receipts() -> None:
    task = _task()
    baseline = _executor("interpreter", "deterministic_program", baseline=True)
    agent = _executor("agent-program", "agent_authored_program")
    first = plan_execution_market(task, (baseline, agent))
    assert first["routing_mode"] == "baseline_with_shadow_probes"
    assert first["shadow_executor_ids"] == ["agent-program"]

    receipts = tuple(
        ExecutionReceipt(
            task_sha256=task.task_sha256,
            task_family=task.task_family,
            executor=agent,
            attempted_at=f"2026-08-{index + 1:02d}T00:00:00Z",
            wallclock_s=10.0,
            marginal_cost=1.0,
            carrier_live=True,
            output_sha256=f"{index:064x}",
            verifier_id=task.verifier_id,
            verifier_version=task.verifier_version,
            verifier_independent=True,
            verification_passed=True,
            residual=0.0,
            reason_codes=("verified",),
            authority_granted="analytical_shadow",
        )
        for index in range(20)
    )
    repeated = plan_execution_market(task, (baseline, agent), receipts)
    assert repeated["routing_mode"] == "baseline_with_shadow_probes"
    assert repeated["capability_snapshots"][1]["distinct_task_count"] == 1

    diversified = tuple(
        replace(receipt, task_sha256=f"{index + 1:064x}")
        for index, receipt in enumerate(receipts)
    )
    promoted = plan_execution_market(task, (baseline, agent), diversified)
    assert promoted["routing_mode"] == "active_verified_route"
    assert promoted["primary_executor_id"] == "agent-program"


def test_implied_growth_verifier_checks_value_residual() -> None:
    task = _task()
    expected = solve_implied_growth(
        market_price=100.0,
        owner_earnings=8.0,
        discount_rate=0.10,
        terminal_growth=0.025,
        horizon_years=10,
        excess_net_cash=0.0,
        shares=1.0,
    )
    assert verify_implied_growth_candidate(task, expected)["passed"] is True
    rejected = verify_implied_growth_candidate(task, expected + 0.05)
    assert rejected["passed"] is False
    assert "present_value_residual_exceeds_tolerance" in rejected["reason_codes"]


def test_authored_solver_must_generalize_to_post_generation_cases() -> None:
    task = _task()
    program = f'''import json
def solve(case):
    def value(g):
        cash=case["owner_earnings"]
        total=0.0
        for year in range(1,int(case["horizon_years"])+1):
            cash*=1.0+g
            total+=cash/(1.0+case["discount_rate"])**year
        total+=cash*(1.0+case["terminal_growth"])/(case["discount_rate"]-case["terminal_growth"])/(1.0+case["discount_rate"])**int(case["horizon_years"])
        return total
    target=case["market_price"]*case["shares"]-case["excess_net_cash"]
    low,high=-0.95,1.5
    for _ in range(300):
        mid=(low+high)/2.0
        if value(mid)<target: low=mid
        else: high=mid
    return (low+high)/2.0
case={json.dumps(task.input_payload, sort_keys=True)}
print(json.dumps({{"schema":"implied-growth-v1","task_sha256":"{task.task_sha256}","implied_growth":solve(case)}}))'''
    rows = _run_program_counterfactuals(program, task, sample_tag="unseen-suite")
    assert len(rows) == 3
    assert all(row["verification"]["passed"] for row in rows)
