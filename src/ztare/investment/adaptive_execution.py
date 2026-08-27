"""JaggedThoughts adapter for capability-adaptive valuation execution.

The first task family is price-implied growth.  One source-bound valuation
program is frozen into a common task contract and attempted through four live
execution modes: the valuation interpreter, direct frontier-agent reasoning, a
frontier-agent-authored Python program, and a hybrid requiring agreement between
both neural paths.  The existing valuation carrier independently checks every
agent-derived output, including post-generation counterfactual cases.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.common.execution_market import (
    ExecutionReceipt,
    ExecutionTask,
    ExecutorIdentity,
    plan_execution_market,
)
from ztare.common.sandboxed_python import run_guarded_script
from ztare.leanmill.frontier_agent_runtime import (
    FrontierAgentConfig,
    SubscriptionJSONRole,
)

from .golden_store import GoldenLeaf, GoldenStore
from .valuation import present_value_owner_earnings, solve_implied_growth


EXECUTION_MARKET_RUN_SCHEMA = "jaggedthoughts-execution-market-run-v1"
IMPLIED_GROWTH_TASK_FAMILY = "jaggedthoughts.valuation.implied_growth"
IMPLIED_GROWTH_OUTPUT_SCHEMA = "jaggedthoughts-implied-growth-solution-v1"
_PROMPT_CONTRACT_VERSION = "jaggedthoughts-implied-growth-executor-prompt-v2"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def implied_growth_agent_output_schema() -> dict[str, Any]:
    """Codex-strict response schema for the paired neural execution lanes."""

    number = {"type": "number"}
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "schema": {"type": "string", "const": "jaggedthoughts-implied-growth-agent-attempt-v1"},
            "task_sha256": {"type": "string"},
            "direct_answer": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "implied_growth": number,
                    "method_summary": {"type": "string"},
                },
                "required": ["implied_growth", "method_summary"],
            },
            "program_source": {"type": "string"},
            "assumption_check": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "target_operating_equity_value": number,
                    "discount_exceeds_terminal": {"type": "boolean"},
                    "bracket_low_value": number,
                    "bracket_high_value": number,
                },
                "required": [
                    "target_operating_equity_value",
                    "discount_exceeds_terminal",
                    "bracket_low_value",
                    "bracket_high_value",
                ],
            },
            "notes": {"type": "string"},
        },
        "required": [
            "schema", "task_sha256", "direct_answer", "program_source",
            "assumption_check", "notes",
        ],
    }


def _selected_assumption(
    assumptions: Mapping[str, Mapping[str, Any]],
    assumption_ids: Iterable[str],
    kind: str,
) -> Mapping[str, Any]:
    matches = [
        assumptions[assumption_id]
        for assumption_id in assumption_ids
        if assumption_id in assumptions
        and str(assumptions[assumption_id].get("assumption_type")) == kind
    ]
    if len(matches) != 1:
        raise ValueError(f"implied-growth program must bind exactly one {kind}, found {len(matches)}")
    return matches[0]


def _compile_task_from_decision(
    decision: Mapping[str, Any],
    *,
    program_id: str | None = None,
) -> tuple[ExecutionTask, dict[str, Any]]:
    envelope = decision.get("valuation_envelope")
    if not isinstance(envelope, Mapping):
        raise ValueError("decision has no valuation envelope")
    results = [
        row for row in (envelope.get("results") or [])
        if isinstance(row, Mapping) and row.get("result_type") == "ImpliedGrowth"
    ]
    if program_id:
        results = [row for row in results if str(row.get("program_id")) == program_id]
    if not results:
        raise ValueError("decision has no matching implied-growth program")
    # Prefer the market's current implied-ERP program, then stable program id.
    result = min(
        results,
        key=lambda row: (
            "erp::current-implied-erp" not in set(row.get("assumption_ids") or []),
            str(row.get("program_id") or ""),
        ),
    )
    assumptions = {
        str(row.get("assumption_id")): row
        for row in (envelope.get("assumptions") or [])
        if isinstance(row, Mapping) and row.get("assumption_id")
    }
    selected_ids = tuple(str(row) for row in (result.get("assumption_ids") or []))
    market_price = _selected_assumption(assumptions, selected_ids, "MarketPrice")
    earnings = _selected_assumption(assumptions, selected_ids, "OwnerEarnings")
    terminal = _selected_assumption(assumptions, selected_ids, "TerminalGrowth")
    horizon = _selected_assumption(assumptions, selected_ids, "Horizon")
    cash = _selected_assumption(assumptions, selected_ids, "ExcessNetCash")
    shares = _selected_assumption(assumptions, selected_ids, "Shares")
    discount_rows = [
        assumptions[assumption_id]
        for assumption_id in selected_ids
        if assumption_id in assumptions
        and assumptions[assumption_id].get("assumption_type") == "DiscountRate"
    ]
    if discount_rows:
        if len(discount_rows) != 1:
            raise ValueError("implied-growth program has ambiguous DiscountRate")
        discount = float(discount_rows[0]["value"])
        discount_derivation = {
            "kind": "declared_discount_rate",
            "assumption_ids": [discount_rows[0]["assumption_id"]],
        }
    else:
        risk_free = _selected_assumption(assumptions, selected_ids, "RiskFreeRate")
        premium = _selected_assumption(assumptions, selected_ids, "EquityRiskPremium")
        beta = _selected_assumption(assumptions, selected_ids, "EquityBeta")
        discount = float(risk_free["value"]) + float(premium["value"]) * float(beta["value"])
        discount_derivation = {
            "kind": "cost_of_equity",
            "risk_free_rate": float(risk_free["value"]),
            "equity_risk_premium": float(premium["value"]),
            "equity_beta": float(beta["value"]),
            "assumption_ids": [
                risk_free["assumption_id"], premium["assumption_id"], beta["assumption_id"],
            ],
        }
    inputs = {
        "operation": "implied_growth",
        "market_price": float(market_price["value"]),
        "owner_earnings": float(earnings["value"]),
        "discount_rate": discount,
        "discount_derivation": discount_derivation,
        "terminal_growth": float(terminal["value"]),
        "horizon_years": int(float(horizon["value"])),
        "excess_net_cash": float(cash["value"]),
        "shares": float(shares["value"]),
        "root_bracket": [-0.95, 1.5],
        "currency": str((decision.get("entity") or {}).get("currency") or "USD"),
        "entity_id": str((decision.get("entity") or {}).get("entity_id") or ""),
        "valuation_program_id": str(result.get("program_id") or ""),
        "valuation_expression": str(result.get("expression") or ""),
        "assumption_ids": list(selected_ids),
        "source_refs": list(result.get("source_refs") or []),
    }
    evidence_sha256s = tuple(
        str(value) for value in (
            decision.get("decision_record_sha256"),
            envelope.get("envelope_sha256"),
            result.get("result_sha256"),
            decision.get("profile_source_sha256"),
        ) if isinstance(value, str) and len(value) == 64
    )
    task = ExecutionTask(
        task_id=(
            f"{inputs['entity_id']}::implied_growth::{inputs['valuation_program_id']}"
        ),
        task_family=IMPLIED_GROWTH_TASK_FAMILY,
        task_version="1",
        input_payload=inputs,
        evidence_sha256s=evidence_sha256s,
        output_schema=IMPLIED_GROWTH_OUTPUT_SCHEMA,
        verifier_id="jaggedthoughts.valuation.implied_growth_residual",
        verifier_version="1",
        verifier_kind="numeric_residual_and_oracle_equivalence",
        tolerance=1e-8,
        consequence_class="paper_analysis_shadow",
        authority_ceiling="analytical_shadow",
        max_wallclock_s=900,
    )
    source = {
        "decision_id": decision.get("decision_id"),
        "decision_record_sha256": decision.get("decision_record_sha256"),
        "valuation_envelope_sha256": envelope.get("envelope_sha256"),
        "valuation_result_sha256": result.get("result_sha256"),
        "valuation_result": dict(result),
    }
    return task, source


def latest_operator_decision(
    root: Path, decision_id: str | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Return one exact operator decision for source-bound execution tasks."""
    candidates: list[tuple[str, str, Path, dict[str, Any]]] = []
    for path in sorted((root / "decisions").glob("*.json")):
        row = _read_json(path)
        if not row or row.get("schema") != "jaggedthoughts-investment-decision-v1":
            continue
        if decision_id and str(row.get("decision_id")) != decision_id:
            continue
        lifecycle = row.get("profile_lifecycle") or {}
        if not decision_id and str(lifecycle.get("data_class") or "") != "operator":
            continue
        candidates.append((str(row.get("as_of") or ""), str(row.get("decision_id") or ""), path, row))
    if not candidates:
        label = decision_id or "an operator decision"
        raise FileNotFoundError(f"execution market could not find {label}")
    _, _, path, row = max(candidates, key=lambda item: (item[0], item[1]))
    return path, row


def subscription_runtime_version(runtime: str) -> str:
    """Read the subscription CLI version captured in executor identity."""
    try:
        proc = subprocess.run(
            [runtime, "--version"], capture_output=True, text=True, timeout=10,
        )
        return ((proc.stdout or proc.stderr or "").strip() or f"{runtime}:unknown")[:160]
    except (OSError, subprocess.TimeoutExpired):
        return f"{runtime}:unavailable"


def _executor_identities(
    config: FrontierAgentConfig,
    *,
    attempted_at: str,
) -> tuple[ExecutorIdentity, ...]:
    valuation_path = Path(__file__).with_name("valuation.py")
    sandbox_path = _repo_root() / "src" / "ztare" / "common" / "sandboxed_python.py"
    schema = implied_growth_agent_output_schema()
    runtime_version = subscription_runtime_version(config.runtime)
    declared_epoch = str(
        os.environ.get("ZTARE_INVESTMENT_EXECUTION_CAPABILITY_EPOCH")
        or attempted_at[:7]
    ).strip()
    epoch_payload = {
        "declared_epoch": declared_epoch,
        "runtime": config.runtime,
        "runtime_version": runtime_version,
        "model": config.model,
        "reasoning_effort": config.reasoning_effort,
        "prompt_contract": _PROMPT_CONTRACT_VERSION,
        "output_schema": schema,
    }
    epoch = f"{declared_epoch}::{stable_sha256(epoch_payload)[:16]}"
    agent_contract_sha = stable_sha256(epoch_payload)
    return (
        ExecutorIdentity(
            executor_id="valuation_interpreter",
            mode="deterministic_program",
            implementation_id="ztare.investment.valuation.solve_implied_growth",
            implementation_sha256=_file_sha256(valuation_path),
            runtime="python",
            model="none",
            reasoning_effort="none",
            capability_epoch=_file_sha256(valuation_path)[:20],
            baseline=True,
            estimated_marginal_cost=0.0,
        ),
        ExecutorIdentity(
            executor_id=f"{config.runtime}_direct_reasoning",
            mode="direct_agent",
            implementation_id=_PROMPT_CONTRACT_VERSION,
            implementation_sha256=agent_contract_sha,
            runtime=config.runtime,
            model=config.model,
            reasoning_effort=config.reasoning_effort,
            capability_epoch=epoch,
            estimated_marginal_cost=1.0,
        ),
        ExecutorIdentity(
            executor_id=f"{config.runtime}_authored_program",
            mode="agent_authored_program",
            implementation_id=f"{_PROMPT_CONTRACT_VERSION}+ztare.common.sandboxed_python",
            implementation_sha256=stable_sha256({
                "agent_contract_sha256": agent_contract_sha,
                "sandbox_sha256": _file_sha256(sandbox_path),
            }),
            runtime=config.runtime,
            model=config.model,
            reasoning_effort=config.reasoning_effort,
            capability_epoch=epoch,
            estimated_marginal_cost=1.0,
        ),
        ExecutorIdentity(
            executor_id=f"{config.runtime}_verified_hybrid",
            mode="verified_hybrid",
            implementation_id=(
                f"{_PROMPT_CONTRACT_VERSION}+ztare.common.sandboxed_python+"
                "jaggedthoughts.valuation.implied_growth_residual"
            ),
            implementation_sha256=stable_sha256({
                "agent_contract_sha256": agent_contract_sha,
                "sandbox_sha256": _file_sha256(sandbox_path),
                "verifier_sha256": _file_sha256(Path(__file__)),
                "composition": "direct_and_program_agreement_v1",
            }),
            runtime=config.runtime,
            model=config.model,
            reasoning_effort=config.reasoning_effort,
            capability_epoch=epoch,
            estimated_marginal_cost=1.0,
        ),
    )


def _render_prompt(task: ExecutionTask) -> str:
    return f"""You are one execution lane in a capability tournament. Solve the frozen
valuation task below twice: first by direct reasoning, then by writing a self-contained Python
program. Return only the strict JSON object requested by the response schema.

TASK CONTRACT
{json.dumps(task.to_dict(), indent=2, sort_keys=True)}

The economics are fixed:
- target operating equity value = market_price * shares - excess_net_cash
- cash flow in year t = owner_earnings * (1 + g)^t
- explicit present value is the sum of each cash flow discounted by (1+r)^t
- continuing value at the horizon is cash_horizon * (1+terminal_growth) /
  (discount_rate-terminal_growth), discounted back to today
- implied_growth is the root where total present value equals target operating equity value
- use the declared bracket [-0.95, 1.5]

For direct_answer, calculate the root and report a finite decimal.
For program_source, emit a complete program that imports only json and/or math and defines
`solve(case)`, where case is an object with the seven numeric keys market_price, owner_earnings,
discount_rate, terminal_growth, horizon_years, excess_net_cash, and shares. The function must
derive and return implied growth by bounded bisection for any admissible case; do not read those
inputs from globals. After the function, embed the frozen numeric case, call solve(case), and print
one JSON object with keys
"schema", "task_sha256", and "implied_growth". Do not access files, environment variables,
network, subprocesses, dynamic evaluation, or user input. The program must be suitable for the
repository's guarded Python runner. Do not copy the valuation_result value from any source; derive
the answer from the task inputs. Preserve task_sha256 exactly. Keep the program free of comments
and prose so forbidden capability words cannot appear incidentally.
"""


def _oracle(task: ExecutionTask) -> float:
    values = task.input_payload
    return solve_implied_growth(
        market_price=float(values["market_price"]),
        owner_earnings=float(values["owner_earnings"]),
        discount_rate=float(values["discount_rate"]),
        terminal_growth=float(values["terminal_growth"]),
        horizon_years=int(values["horizon_years"]),
        excess_net_cash=float(values["excess_net_cash"]),
        shares=float(values["shares"]),
    )


def verify_implied_growth_candidate(task: ExecutionTask, value: Any) -> dict[str, Any]:
    """Independently settle one candidate against DCF residual and canonical root."""

    try:
        candidate = float(value)
        if not math.isfinite(candidate):
            raise ValueError("candidate is not finite")
        values = task.input_payload
        target = float(values["market_price"]) * float(values["shares"])
        target -= float(values["excess_net_cash"])
        present = present_value_owner_earnings(
            float(values["owner_earnings"]),
            candidate,
            int(values["horizon_years"]),
            float(values["discount_rate"]),
            float(values["terminal_growth"]),
        )
        oracle = _oracle(task)
        absolute = abs(present - target)
        relative = absolute / max(1.0, abs(target))
        oracle_delta = abs(candidate - oracle)
        passed = (
            -0.95 <= candidate <= 1.5
            and relative <= task.tolerance
            and oracle_delta <= task.tolerance
        )
        reasons = ["numeric_residual_passed", "oracle_equivalence_passed"] if passed else []
        if not -0.95 <= candidate <= 1.5:
            reasons.append("outside_declared_root_bracket")
        if relative > task.tolerance:
            reasons.append("present_value_residual_exceeds_tolerance")
        if oracle_delta > task.tolerance:
            reasons.append("oracle_delta_exceeds_tolerance")
        return {
            "schema": "jaggedthoughts-implied-growth-verification-v1",
            "passed": passed,
            "candidate": candidate,
            "oracle": oracle,
            "absolute_value_residual": absolute,
            "relative_value_residual": relative,
            "oracle_delta": oracle_delta,
            "tolerance": task.tolerance,
            "reason_codes": reasons,
        }
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        return {
            "schema": "jaggedthoughts-implied-growth-verification-v1",
            "passed": False,
            "candidate": None,
            "oracle": _oracle(task),
            "absolute_value_residual": None,
            "relative_value_residual": None,
            "oracle_delta": None,
            "tolerance": task.tolerance,
            "reason_codes": ["invalid_candidate"],
            "error": str(error)[:500],
        }


def _counterfactual_tasks(task: ExecutionTask, sample_tag: str) -> tuple[ExecutionTask, ...]:
    """Create post-generation cases that a returned solver could not have memorized."""

    base = dict(task.input_payload)
    digest = stable_sha256({"task_sha256": task.task_sha256, "sample_tag": sample_tag})
    jitter = (int(digest[:8], 16) / 0xFFFFFFFF - 0.5) * 0.04
    variants = (
        {**base, "market_price": float(base["market_price"]) * (0.86 + jitter)},
        {
            **base,
            "market_price": float(base["market_price"]) * (1.12 + jitter),
            "owner_earnings": float(base["owner_earnings"]) * 0.94,
        },
        {
            **base,
            "discount_rate": float(base["discount_rate"]) + 0.013,
            "terminal_growth": max(-0.25, float(base["terminal_growth"]) - 0.006),
            "excess_net_cash": float(base["excess_net_cash"]) * 0.82,
        },
    )
    out: list[ExecutionTask] = []
    for index, values in enumerate(variants, start=1):
        # Remove source-shape fields.  The generated function receives only
        # the seven numeric coordinates named in its interface contract.
        numeric = {
            key: values[key]
            for key in (
                "market_price", "owner_earnings", "discount_rate", "terminal_growth",
                "horizon_years", "excess_net_cash", "shares",
            )
        }
        candidate = ExecutionTask(
            task_id=f"{task.task_id}::counterfactual::{index}",
            task_family=task.task_family,
            task_version=task.task_version,
            input_payload=numeric,
            evidence_sha256s=(task.task_sha256,),
            output_schema=task.output_schema,
            verifier_id=task.verifier_id,
            verifier_version=task.verifier_version,
            verifier_kind=task.verifier_kind,
            tolerance=task.tolerance,
            consequence_class="capability_counterfactual",
            authority_ceiling=task.authority_ceiling,
            max_wallclock_s=15,
        )
        try:
            _oracle(candidate)
        except ValueError:
            continue
        out.append(candidate)
    return tuple(out)


def _run_program_counterfactuals(
    program_source: str,
    task: ExecutionTask,
    *,
    sample_tag: str,
) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for hidden in _counterfactual_tasks(task, sample_tag):
        case = dict(hidden.input_payload)
        appended = (
            program_source
            + "\n_hidden_case=" + json.dumps(case, sort_keys=True, separators=(",", ":"))
            + "\n_hidden_growth=solve(_hidden_case)"
            + "\nprint(json.dumps({\"schema\":\"jaggedthoughts-implied-growth-solution-v1\","
            + f"\"task_sha256\":\"{hidden.task_sha256}\","
            + "\"implied_growth\":_hidden_growth},separators=(\",\",\":\")))\n"
        )
        output = run_guarded_script(appended, timeout_s=15)
        identity_ok = bool(output and str(output.get("task_sha256")) == hidden.task_sha256)
        verification = (
            verify_implied_growth_candidate(hidden, output.get("implied_growth"))
            if identity_ok and output is not None
            else {
                "schema": "jaggedthoughts-implied-growth-verification-v1",
                "passed": False,
                "relative_value_residual": None,
                "reason_codes": ["counterfactual_program_failed"],
            }
        )
        rows.append({
            "task_sha256": hidden.task_sha256,
            "input_payload": case,
            "output": output,
            "verification": verification,
        })
    return tuple(rows)


def _program_suite_verification(
    primary: Mapping[str, Any],
    counterfactuals: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    counterfactual_passes = sum(
        bool((row.get("verification") or {}).get("passed"))
        for row in counterfactuals
    )
    expected_count = 3
    passed = bool(primary.get("passed")) and (
        len(counterfactuals) == expected_count
        and counterfactual_passes == expected_count
    )
    residuals = [
        float(value)
        for value in [
            primary.get("relative_value_residual"),
            *[
                (row.get("verification") or {}).get("relative_value_residual")
                for row in counterfactuals
            ],
        ]
        if value is not None
    ]
    reasons: list[str] = []
    if primary.get("passed"):
        reasons.append("primary_case_verified")
    else:
        reasons.extend(primary.get("reason_codes") or ["primary_case_failed"])
    if len(counterfactuals) != expected_count:
        reasons.append("counterfactual_suite_incomplete")
    elif counterfactual_passes == expected_count:
        reasons.append("counterfactual_suite_verified")
    else:
        reasons.append("counterfactual_suite_failed")
    return {
        "schema": "jaggedthoughts-program-suite-verification-v1",
        "passed": passed,
        "candidate": primary.get("candidate"),
        "oracle": primary.get("oracle"),
        "relative_value_residual": max(residuals) if residuals else None,
        "reason_codes": reasons,
        "primary_case": dict(primary),
        "counterfactual_case_count": len(counterfactuals),
        "counterfactual_pass_count": counterfactual_passes,
        "counterfactuals": list(counterfactuals),
    }


def _hybrid_verification(
    direct: Mapping[str, Any],
    program: Mapping[str, Any],
    *,
    tolerance: float,
) -> dict[str, Any]:
    direct_candidate = direct.get("candidate")
    program_candidate = program.get("candidate")
    agreement = (
        abs(float(direct_candidate) - float(program_candidate))
        if direct_candidate is not None and program_candidate is not None
        else None
    )
    residuals = [
        float(value)
        for value in (
            direct.get("relative_value_residual"),
            program.get("relative_value_residual"),
            agreement,
        )
        if value is not None
    ]
    passed = bool(direct.get("passed")) and bool(program.get("passed")) and (
        agreement is not None and agreement <= tolerance
    )
    return {
        "schema": "jaggedthoughts-verified-hybrid-verification-v1",
        "passed": passed,
        "candidate": program_candidate,
        "oracle": program.get("oracle"),
        "relative_value_residual": max(residuals) if residuals else None,
        "direct_program_agreement": agreement,
        "tolerance": tolerance,
        "reason_codes": (
            ["direct_verified", "program_suite_verified", "paths_agree"]
            if passed else ["hybrid_component_or_agreement_failed"]
        ),
        "direct_component": dict(direct),
        "program_component": dict(program),
    }


def _receipt(
    task: ExecutionTask,
    executor: ExecutorIdentity,
    *,
    attempted_at: str,
    wallclock_s: float,
    marginal_cost: float,
    carrier_live: bool,
    output: Mapping[str, Any] | None,
    verification: Mapping[str, Any],
    verifier_independent: bool,
) -> ExecutionReceipt:
    return ExecutionReceipt(
        task_sha256=task.task_sha256,
        task_family=task.task_family,
        executor=executor,
        attempted_at=attempted_at,
        wallclock_s=wallclock_s,
        marginal_cost=marginal_cost,
        carrier_live=carrier_live,
        output_sha256=stable_sha256(dict(output)) if output else "",
        verifier_id=task.verifier_id,
        verifier_version=task.verifier_version,
        verifier_independent=verifier_independent,
        verification_passed=bool(verification.get("passed")),
        residual=(
            float(verification["relative_value_residual"])
            if verification.get("relative_value_residual") is not None else None
        ),
        reason_codes=tuple(verification.get("reason_codes") or ["verification_failed"]),
        authority_granted=task.authority_ceiling,
    )


def _receipt_from_dict(value: Mapping[str, Any]) -> ExecutionReceipt:
    raw_executor = dict(value.get("executor") or {})
    executor = ExecutorIdentity(**{
        key: raw_executor[key]
        for key in (
            "executor_id", "mode", "implementation_id", "implementation_sha256",
            "runtime", "model", "reasoning_effort", "capability_epoch", "baseline",
            "estimated_marginal_cost",
        )
    })
    return ExecutionReceipt(**{
        "task_sha256": value["task_sha256"],
        "task_family": value["task_family"],
        "executor": executor,
        "attempted_at": value["attempted_at"],
        "wallclock_s": value["wallclock_s"],
        "marginal_cost": value["marginal_cost"],
        "carrier_live": value["carrier_live"],
        "output_sha256": value.get("output_sha256") or "",
        "verifier_id": value["verifier_id"],
        "verifier_version": value["verifier_version"],
        "verifier_independent": value["verifier_independent"],
        "verification_passed": value["verification_passed"],
        "residual": value.get("residual"),
        "reason_codes": tuple(value.get("reason_codes") or ()),
        "authority_granted": value["authority_granted"],
    })


def execution_market_receipts(root: Path) -> tuple[ExecutionReceipt, ...]:
    receipts: list[ExecutionReceipt] = []
    for path in sorted((root / "execution_market" / "runs").glob("*.json")):
        run = _read_json(path)
        if not run or run.get("schema") != EXECUTION_MARKET_RUN_SCHEMA:
            continue
        for lane in run.get("lanes") or []:
            try:
                receipts.append(_receipt_from_dict(lane["receipt"]))
            except (KeyError, TypeError, ValueError):
                continue
    return tuple(receipts)


def execution_market_status(root: Path) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    for path in sorted((root / "execution_market" / "runs").glob("*.json"), reverse=True):
        row = _read_json(path)
        if row and row.get("schema") == EXECUTION_MARKET_RUN_SCHEMA:
            runs.append({**row, "run_path": path.relative_to(root).as_posix()})
    runs.sort(
        key=lambda row: (str(row.get("completed_at") or ""), str(row.get("run_id") or "")),
        reverse=True,
    )
    latest = runs[0] if runs else None
    receipts = execution_market_receipts(root)
    return {
        "schema": "jaggedthoughts-execution-market-status-v1",
        "enabled": True,
        "task_family": IMPLIED_GROWTH_TASK_FAMILY,
        "run_count": len(runs),
        "receipt_count": len(receipts),
        "verified_agent_receipt_count": sum(
            row.admissible_label and row.verification_passed
            for row in receipts
            if row.executor.mode != "deterministic_program"
        ),
        "latest_run": latest,
        "routing_rule": (
            "Use bounded shadow probes until same-family, same-epoch receipts qualify an executor; "
            "then select within the verified cost/latency Pareto frontier."
        ),
        "capital_authority": False,
    }


def _record_run_leaf(
    *,
    owner: str,
    store_path: Path,
    run: Mapping[str, Any],
) -> str:
    leaf = GoldenLeaf(
        owner=owner,
        object_kind="execution_market_run",
        object_id=str(run["run_id"]),
        epoch=str(run["task"]["task_sha256"]),
        occurred_at=str(run["attempted_at"]),
        available_at=str(run["completed_at"]),
        payload=dict(run),
        source_refs=tuple(
            [str(run["source"]["decision_id"])]
            + list((run.get("task") or {}).get("input_payload", {}).get("source_refs") or [])
        ),
    )
    GoldenStore(store_path).append_bundle((leaf,), make_heads=True)
    return leaf.leaf_sha256


def run_execution_market_probe(
    root: Path,
    *,
    owner: str,
    store_path: Path,
    decision_id: str | None = None,
    program_id: str | None = None,
    config: FrontierAgentConfig | None = None,
    agent_result: Mapping[str, Any] | None = None,
    sample_tag: str | None = None,
) -> dict[str, Any]:
    """Run or replay one source-bound, four-mode valuation tournament."""

    decision_path, decision = latest_operator_decision(root, decision_id)
    task, source = _compile_task_from_decision(decision, program_id=program_id)
    attempted_at = _utc_now()
    sample_tag = str(sample_tag or attempted_at).strip()
    config = config or FrontierAgentConfig(
        runtime="codex", model="account-default", reasoning_effort="high",
        timeout_seconds=task.max_wallclock_s, web_research=False,
    )
    executors = _executor_identities(config, attempted_at=attempted_at)
    run_id = (
        f"implied-growth-{task.task_sha256[:16]}-"
        f"{stable_sha256({'executors': [row.to_dict() for row in executors], 'sample_tag': sample_tag})[:12]}"
    )
    run_path = root / "execution_market" / "runs" / f"{run_id}.json"
    prior = _read_json(run_path)
    if prior:
        return {**prior, "ok": True, "replayed": True, "run_path": run_path.relative_to(root).as_posix()}

    prior_receipts = execution_market_receipts(root)
    market_before = plan_execution_market(
        task, executors, prior_receipts, max_shadow_executors=3,
    )
    lanes: list[dict[str, Any]] = []

    baseline_output = {
        "schema": IMPLIED_GROWTH_OUTPUT_SCHEMA,
        "task_sha256": task.task_sha256,
        "implied_growth": _oracle(task),
    }
    baseline_verification = verify_implied_growth_candidate(task, baseline_output["implied_growth"])
    lanes.append({
        "executor": executors[0].to_dict(),
        "output": baseline_output,
        "verification": baseline_verification,
        "receipt": _receipt(
            task, executors[0], attempted_at=attempted_at, wallclock_s=0.0,
            marginal_cost=0.0, carrier_live=True, output=baseline_output,
            verification=baseline_verification, verifier_independent=False,
        ).to_dict(),
    })

    provider_started = time.monotonic()
    provider_error: str | None = None
    provider_called = False
    provider_call_ref = ""
    if agent_result is None:
        call_identity = stable_sha256({
            "task_sha256": task.task_sha256,
            "executors": [row.executor_sha256 for row in executors[1:]],
            "sample_tag": sample_tag,
        })
        artifact_dir = root / "execution_market" / "agent_calls" / call_identity
        role = SubscriptionJSONRole(
            role="jaggedthoughts_valuation_executor",
            agent_id=f"jaggedthoughts-valuation-{call_identity[:16]}",
            repo=_repo_root(),
            artifact_dir=artifact_dir,
            config=config,
            output_schema=implied_growth_agent_output_schema(),
        )
        try:
            agent_result = role(_render_prompt(task))
            provider_called = bool(role.provider_call_count)
            provider_call_ref = artifact_dir.relative_to(root).as_posix()
        except Exception as error:  # transport failure is visible and unscored
            provider_error = f"{type(error).__name__}: {error}"[:1_000]
            agent_result = None
    provider_wallclock = max(0.0, time.monotonic() - provider_started)

    if agent_result is not None and str(agent_result.get("task_sha256")) != task.task_sha256:
        provider_error = "agent output task_sha256 does not match the frozen task"
        agent_result = None

    direct_output: dict[str, Any] | None = None
    direct_verification: dict[str, Any]
    if agent_result is not None:
        direct_output = {
            "schema": IMPLIED_GROWTH_OUTPUT_SCHEMA,
            "task_sha256": task.task_sha256,
            "implied_growth": (agent_result.get("direct_answer") or {}).get("implied_growth"),
            "method_summary": (agent_result.get("direct_answer") or {}).get("method_summary"),
        }
        direct_verification = verify_implied_growth_candidate(task, direct_output["implied_growth"])
    else:
        direct_verification = {
            "schema": "jaggedthoughts-implied-growth-verification-v1",
            "passed": False,
            "relative_value_residual": None,
            "reason_codes": ["provider_carrier_unavailable"],
            "error": provider_error,
        }
    lanes.append({
        "executor": executors[1].to_dict(),
        "output": direct_output,
        "verification": direct_verification,
        "receipt": _receipt(
            task, executors[1], attempted_at=attempted_at,
            wallclock_s=provider_wallclock, marginal_cost=1.0 if provider_called else 0.0,
            carrier_live=agent_result is not None, output=direct_output,
            verification=direct_verification, verifier_independent=True,
        ).to_dict(),
    })

    program_started = time.monotonic()
    program_output = None
    if agent_result is not None:
        program_output = run_guarded_script(str(agent_result.get("program_source") or ""), timeout_s=15)
    program_wallclock = provider_wallclock + max(0.0, time.monotonic() - program_started)
    counterfactuals: tuple[dict[str, Any], ...] = ()
    if (
        program_output is not None
        and str(program_output.get("task_sha256")) == task.task_sha256
    ):
        primary_program_verification = verify_implied_growth_candidate(
            task, program_output.get("implied_growth"),
        )
        counterfactuals = _run_program_counterfactuals(
            str(agent_result.get("program_source") or ""),
            task,
            sample_tag=sample_tag,
        )
        program_verification = _program_suite_verification(
            primary_program_verification, counterfactuals,
        )
    else:
        program_verification = {
            "schema": "jaggedthoughts-program-suite-verification-v1",
            "passed": False,
            "relative_value_residual": None,
            "counterfactual_case_count": 0,
            "counterfactual_pass_count": 0,
            "counterfactuals": [],
            "reason_codes": [
                "guarded_program_failed"
                if program_output is None else "program_task_identity_mismatch"
            ],
        }
    lanes.append({
        "executor": executors[2].to_dict(),
        "output": program_output,
        "program_source_sha256": (
            stable_sha256({"program_source": agent_result.get("program_source")})
            if agent_result is not None else None
        ),
        "verification": program_verification,
        "receipt": _receipt(
            task, executors[2], attempted_at=attempted_at,
            wallclock_s=program_wallclock, marginal_cost=1.0 if provider_called else 0.0,
            carrier_live=program_output is not None, output=program_output,
            verification=program_verification, verifier_independent=True,
        ).to_dict(),
    })

    hybrid_verification = _hybrid_verification(
        direct_verification, program_verification, tolerance=task.tolerance,
    )
    hybrid_output = (
        {
            "schema": IMPLIED_GROWTH_OUTPUT_SCHEMA,
            "task_sha256": task.task_sha256,
            "implied_growth": program_verification.get("candidate"),
        }
        if program_verification.get("candidate") is not None else None
    )
    lanes.append({
        "executor": executors[3].to_dict(),
        "output": hybrid_output,
        "verification": hybrid_verification,
        "receipt": _receipt(
            task, executors[3], attempted_at=attempted_at,
            wallclock_s=program_wallclock, marginal_cost=1.0 if provider_called else 0.0,
            carrier_live=hybrid_output is not None, output=hybrid_output,
            verification=hybrid_verification, verifier_independent=True,
        ).to_dict(),
    })

    all_receipts = prior_receipts + tuple(_receipt_from_dict(row["receipt"]) for row in lanes)
    market_after = plan_execution_market(
        task, executors, all_receipts, max_shadow_executors=3,
    )
    completed_at = _utc_now()
    body = {
        "schema": EXECUTION_MARKET_RUN_SCHEMA,
        "run_id": run_id,
        "attempted_at": attempted_at,
        "completed_at": completed_at,
        "task": task.to_dict(),
        "source": {
            **source,
            "decision_path": decision_path.relative_to(root).as_posix(),
        },
        "market_before": market_before,
        "market_after": market_after,
        "lanes": lanes,
        "provider": {
            "runtime": config.runtime,
            "model": config.model,
            "reasoning_effort": config.reasoning_effort,
            "runtime_version": subscription_runtime_version(config.runtime),
            "provider_called": provider_called,
            "provider_call_ref": provider_call_ref,
            "shared_by_executor_ids": [row.executor_id for row in executors[1:]],
            "error": provider_error,
        },
        "cost_unit": "subscription_provider_calls",
        "verification_pass_count": sum(bool(row["verification"].get("passed")) for row in lanes),
        "agent_verification_pass_count": sum(
            bool(row["verification"].get("passed")) for row in lanes[1:]
        ),
        "capital_authority": False,
        "boundary": (
            "This receipt may update same-family executor routing. It cannot activate a paper decision, "
            "change a portfolio, or route an order."
        ),
    }
    run = {**body, "run_sha256": stable_sha256(body)}
    _atomic_json(run_path, run)
    try:
        leaf_sha = _record_run_leaf(
            owner=owner, store_path=store_path, run=run,
        )
    except ValueError:
        # The immutable run file remains the receipt if a pre-existing store
        # identity was already written by a concurrent/replayed action.
        leaf_sha = ""
    return {
        **run,
        "ok": provider_error is None,
        "replayed": False,
        "run_path": run_path.relative_to(root).as_posix(),
        "golden_leaf_sha256": leaf_sha,
    }


__all__ = [
    "EXECUTION_MARKET_RUN_SCHEMA",
    "IMPLIED_GROWTH_TASK_FAMILY",
    "execution_market_receipts",
    "execution_market_status",
    "implied_growth_agent_output_schema",
    "latest_operator_decision",
    "run_execution_market_probe",
    "subscription_runtime_version",
    "verify_implied_growth_candidate",
]
