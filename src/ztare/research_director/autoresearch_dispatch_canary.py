"""Bounded canary for subscription-backed autoresearch dispatch."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator

from ztare.common import utils
from ztare.common.dispatch_model import (
    DispatchTextResponse,
    dispatch_call_text,
)
from ztare.common.subscription_agent_runtime import run_subscription_agent_with_recovery
from ztare.common.subscription_sessions import default_subscription_runtime
from ztare.fit.mutation_suite_guard import (
    validate_python_suite_candidate,
    validate_python_suite_imports,
)
from ztare.validator.candidate_extraction import extract_best_python_candidate
from ztare.validator.core.mutation_contract import (
    MutationMismatchCode,
    evaluate_mutation_declaration,
    parse_mutation_declaration,
)
from ztare.validator.core.meta_judge_schema import (
    coerce_raw_meta_judge_score,
    raw_meta_judge_shape_errors,
)
from ztare.validator.inverter_agent import _parse_or_salvage_inverter_response


CANARY_TOKEN = "ZTARE_DISPATCH_CANARY_OK"
CANARY_CONTRACTS = {"text", "mutator", "judge", "committee", "inverter"}
DEFAULT_PARITY_CONTRACTS = ("text", "mutator", "judge", "committee", "inverter")


def _site_key(call_site: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in call_site.upper()).strip("_")


@contextmanager
def _temporary_env(values: dict[str, str]) -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in values}
    try:
        os.environ.update(values)
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _mock_mutator_response() -> str:
    return """```json
{"scope_delta":"TEST_HARNESS","claim_delta_type":"REFRAMING","primitive_invoked":null,"touched_artifacts":["thesis.md","test_model.py"]}
```

This canary thesis introduces a minimal bounded discriminator surface.

```python
MODEL_PARAMS = {"bias": 1.0}

def I_model(features, params=None):
    params = params or MODEL_PARAMS
    return float(features.get("x", 0.0)) + float(params["bias"])

def test_visible_boundary():
    assert I_model({"x": 0.0}) == 1.0
```
"""


def _mock_judge_response() -> str:
    return json.dumps(
        {
            "score": 42,
            "weakest_point": "canary verdict only",
            "verified_axioms": [],
            "retired_axioms_approved": [],
            "evidence_gaps": [],
            "derived_constraints": [],
            "logic_gaps": ["no substantive thesis was evaluated"],
            "debate_summary": "bounded dispatch canary",
            "adversarial_alignment": "no project claim made",
            "friction_points": [],
            "probability_dag": {
                "outcome": {"label": "canary", "probability": 0.42},
                "nodes": [],
                "edges": [],
            },
        },
        sort_keys=True,
    )


def _mock_committee_response() -> str:
    return json.dumps(
        [
            {
                "role": "Boundary Auditor",
                "persona": "Looks for untested edge cases and hidden fit-window assumptions.",
                "focus_area": "visible-to-held-out generalization",
            },
            {
                "role": "Mechanism Skeptic",
                "persona": "Checks whether the proposed mechanism explains more than the fitted points.",
                "focus_area": "secondary observable pressure",
            },
            {
                "role": "Execution Auditor",
                "persona": "Verifies that the falsification suite actually tests the asserted claim.",
                "focus_area": "test harness solvency",
            },
        ],
        sort_keys=True,
    )


def _mock_inverter_response() -> str:
    return json.dumps(
        {
            "tests": [
                {
                    "category": "measurement_artifact",
                    "munger_inversion": "The signal is produced by preprocessing rather than the claimed mechanism.",
                    "popper_test": "Recompute the score with the preprocessing stage disabled.",
                    "procedure": "Run the candidate on the same fixture data with preprocessing disabled and compare the score delta.",
                    "pass_criterion": "The finding stands if the score remains within 5 percent of the original.",
                    "fail_criterion": "The finding is killed if the score drops by more than 20 percent.",
                    "required_artifacts": ["workspace/latest_eval_results.json"],
                    "instrument_risk": "The fixture may be too small to expose the preprocessing dependency.",
                    "auto_testable": True,
                    "estimated_cost": "cheap",
                },
                {
                    "category": "confound",
                    "munger_inversion": "An unmeasured fixture split explains the improvement.",
                    "popper_test": "Stratify the score by split and require the effect in each split.",
                    "procedure": "Group evaluation rows by split label and recompute the candidate score per group.",
                    "pass_criterion": "The finding stands if every split preserves a positive effect.",
                    "fail_criterion": "The finding is killed if the effect is isolated to one split.",
                    "required_artifacts": ["workspace/fit_trace.json"],
                    "instrument_risk": "Missing split labels make the test uninterpretable.",
                    "auto_testable": False,
                    "estimated_cost": "moderate",
                },
                {
                    "category": "generalization",
                    "munger_inversion": "The candidate only fits the visible development window.",
                    "popper_test": "Evaluate the same candidate on a held-out fixture family.",
                    "procedure": "Run the existing evaluator against a held-out fixture and compare the declared mechanism.",
                    "pass_criterion": "The finding stands if held-out score degradation is below the pre-committed bound.",
                    "fail_criterion": "The finding is killed if the held-out fixture reverses the effect.",
                    "required_artifacts": ["workspace/held_out_eval_results.json"],
                    "instrument_risk": "Held-out fixture mismatch could test a different mechanism.",
                    "auto_testable": True,
                    "estimated_cost": "moderate",
                },
            ],
            "overall_assessment": "The canary champion is vulnerable to fixture and preprocessing artifacts.",
            "confidence_the_champion_survives": 0.42,
        },
        sort_keys=True,
    )


def _fake_subscription_runner(**kwargs: Any) -> object:
    prompt = str(kwargs.get("prompt") or "")
    repo = Path(str(kwargs.get("repo") or "."))
    task_path = repo / "TASK.md"
    if task_path.is_file():
        try:
            prompt = task_path.read_text(encoding="utf-8")
        except OSError:
            pass
    if "MutationDeclaration" in prompt:
        stdout = _mock_mutator_response()
    elif "meta-judge verdict" in prompt:
        stdout = _mock_judge_response()
    elif "committee personas" in prompt:
        stdout = _mock_committee_response()
    elif "falsification tests" in prompt:
        stdout = _mock_inverter_response()
    else:
        stdout = f"{CANARY_TOKEN}\n"
    return SimpleNamespace(
        result=subprocess.CompletedProcess(
            [str(kwargs.get("runtime") or "agent")],
            0,
            stdout=stdout,
            stderr="",
        ),
        final_command=[str(kwargs.get("runtime") or "agent"), "dispatch-canary", "mock"],
        recovery_note=None,
    )


def _mock_response_for_prompt(prompt: str) -> str:
    """Return the fixed canary response matching a typed prompt."""

    if "MutationDeclaration" in prompt:
        return _mock_mutator_response()
    if "meta-judge verdict" in prompt:
        return _mock_judge_response()
    if "committee personas" in prompt:
        return _mock_committee_response()
    if "falsification tests" in prompt:
        return _mock_inverter_response()
    return f"{CANARY_TOKEN}\n"


def _text_prompt() -> str:
    return (
        f"Return exactly this token and nothing else: {CANARY_TOKEN}. "
        "Do not edit files. Do not run commands."
    )


def _mutator_contract_prompt() -> str:
    return """Return exactly two fenced blocks and no extra commentary:

1. A fenced json block containing a MutationDeclaration object with fields:
   scope_delta, claim_delta_type, primitive_invoked, touched_artifacts.
   Use scope_delta TEST_HARNESS, claim_delta_type REFRAMING,
   primitive_invoked null, and touched_artifacts ["thesis.md", "test_model.py"].

2. A fenced python block containing a minimal standalone test_model.py surface.
   It must define I_model(features, params=None) and avoid module-level I_model calls.
   Use only Python standard library features.
"""


def _judge_contract_prompt() -> str:
    return """Return exactly one JSON object and no extra commentary.

The object is a raw meta-judge verdict with these top-level fields:
score, weakest_point, verified_axioms, retired_axioms_approved, evidence_gaps,
derived_constraints, logic_gaps, debate_summary, adversarial_alignment,
friction_points, probability_dag.

Use score 42. weakest_point, debate_summary, and adversarial_alignment must be
strings. Use empty arrays for list fields unless a one-item logic_gaps array is
useful. probability_dag must be an object with outcome, nodes, edges; outcome
must be an object, nodes and edges must be arrays.
This is a bounded dispatch canary; do not evaluate a real project claim.
"""


def _committee_contract_prompt() -> str:
    return """Return exactly one JSON array and no extra commentary.

The array contains exactly 3 committee personas. Each item must be an object
with these string fields: role, persona, focus_area.
This is a bounded dispatch canary; do not evaluate a real project claim.
"""


def _inverter_contract_prompt() -> str:
    return """Return exactly one JSON object and no extra commentary.

The object is an inverter review. It must contain:
- tests: an array with exactly 3 falsification tests.
- overall_assessment: a non-empty string.
- confidence_the_champion_survives: a number from 0.0 to 1.0.

Each test must contain these fields:
category, munger_inversion, popper_test, procedure, pass_criterion,
fail_criterion, required_artifacts, instrument_risk, auto_testable,
estimated_cost.

Use exactly these categories once each:
measurement_artifact, confound, generalization.
This is a bounded dispatch canary; do not evaluate a real project claim.
"""


def _validate_mutator_contract(text: str) -> dict[str, Any]:
    match = re.search(r"```json\s*(\{.*?\})\s*```", text or "", re.DOTALL)
    if not match:
        raise ValueError("missing fenced MutationDeclaration json block")
    declaration = parse_mutation_declaration(utils.parse_llm_json(match.group(1)))
    remaining = ((text or "")[: match.start()] + (text or "")[match.end():]).strip()
    extraction = extract_best_python_candidate(remaining, {})
    validate_python_suite_candidate(extraction.python_code)
    validate_python_suite_imports(
        extraction.python_code or "",
        require_i_model=True,
        require_parametric_form=False,
        rubric_data={},
    )
    validation = evaluate_mutation_declaration(
        declaration,
        ("projects/canary/thesis.md", "projects/canary/test_model.py"),
        before_text="Baseline thesis.",
        after_text=extraction.clean_thesis,
        approved_primitive_keys=(),
    )
    if validation.mismatch_code != MutationMismatchCode.CLEAN:
        raise ValueError(
            "mutation declaration mismatch: "
            f"{validation.mismatch_code.value}: {validation.rationale}"
        )
    return {
        "mutation_declaration": {
            "scope_delta": declaration.scope_delta.value,
            "claim_delta_type": declaration.claim_delta_type.value,
            "primitive_invoked": declaration.primitive_invoked,
            "touched_artifacts": [item.value for item in declaration.touched_artifacts],
        },
        "candidate_extraction": {
            "python_code_present": bool(extraction.python_code),
            "selected_score": extraction.selected_score,
            "num_python_blocks": extraction.num_python_blocks,
            "num_fenced_blocks": extraction.num_fenced_blocks,
            "auto_repaired": extraction.auto_repaired,
        },
        "mutation_validation": {
            "mismatch_code": validation.mismatch_code.value,
            "rationale": validation.rationale,
        },
    }


def _validate_judge_contract(text: str) -> dict[str, Any]:
    payload = utils.parse_llm_json(text or "")
    errors = raw_meta_judge_shape_errors(payload)
    if errors:
        raise ValueError(f"judge verdict shape errors: {', '.join(errors)}")
    coerced = coerce_raw_meta_judge_score(payload)
    return {
        "score": coerced.get("score"),
        "weakest_point": coerced.get("weakest_point"),
        "logic_gap_count": len(coerced.get("logic_gaps") or []),
        "probability_dag_keys": sorted((coerced.get("probability_dag") or {}).keys()),
    }


def _validate_committee_contract(text: str) -> dict[str, Any]:
    payload = utils.parse_llm_json(text or "")
    if not isinstance(payload, list):
        raise ValueError("committee response must be a JSON array")
    if len(payload) != 3:
        raise ValueError(f"committee response must contain exactly 3 personas, got {len(payload)}")
    required = {"role", "persona", "focus_area"}
    roles: list[str] = []
    focus_areas: list[str] = []
    for idx, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"committee[{idx}] must be an object")
        missing = sorted(required - set(item))
        if missing:
            raise ValueError(f"committee[{idx}] missing required field(s): {', '.join(missing)}")
        for field in required:
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError(f"committee[{idx}].{field} must be a non-empty string")
        roles.append(item["role"].strip())
        focus_areas.append(item["focus_area"].strip())
    return {
        "persona_count": len(payload),
        "roles": roles,
        "focus_areas": focus_areas,
    }


def _validate_inverter_contract(text: str) -> dict[str, Any]:
    payload = _parse_or_salvage_inverter_response(text or "")
    if not isinstance(payload, dict):
        raise ValueError("inverter response must be a JSON object")
    tests = payload.get("tests")
    if not isinstance(tests, list):
        raise ValueError("inverter response must contain tests array")
    if len(tests) != 3:
        raise ValueError(f"inverter response must contain exactly 3 tests, got {len(tests)}")
    assessment = payload.get("overall_assessment")
    if not isinstance(assessment, str) or not assessment.strip():
        raise ValueError("overall_assessment must be a non-empty string")
    confidence = payload.get("confidence_the_champion_survives")
    if not isinstance(confidence, (int, float)) or not 0.0 <= float(confidence) <= 1.0:
        raise ValueError("confidence_the_champion_survives must be a number from 0.0 to 1.0")

    required = {
        "category",
        "munger_inversion",
        "popper_test",
        "procedure",
        "pass_criterion",
        "fail_criterion",
        "required_artifacts",
        "instrument_risk",
        "auto_testable",
        "estimated_cost",
    }
    categories: list[str] = []
    auto_testable_count = 0
    for idx, item in enumerate(tests):
        if not isinstance(item, dict):
            raise ValueError(f"inverter.tests[{idx}] must be an object")
        missing = sorted(required - set(item))
        if missing:
            raise ValueError(f"inverter.tests[{idx}] missing required field(s): {', '.join(missing)}")
        for field in required - {"required_artifacts", "auto_testable"}:
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError(f"inverter.tests[{idx}].{field} must be a non-empty string")
        artifacts = item.get("required_artifacts")
        if not isinstance(artifacts, list) or not all(isinstance(a, str) and a.strip() for a in artifacts):
            raise ValueError(f"inverter.tests[{idx}].required_artifacts must be a non-empty string array")
        if not isinstance(item.get("auto_testable"), bool):
            raise ValueError(f"inverter.tests[{idx}].auto_testable must be boolean")
        categories.append(item["category"].strip())
        auto_testable_count += int(bool(item["auto_testable"]))

    expected_categories = ["confound", "generalization", "measurement_artifact"]
    if sorted(categories) != expected_categories:
        raise ValueError(f"inverter categories must be {expected_categories}, got {sorted(categories)}")
    return {
        "test_count": len(tests),
        "categories": categories,
        "auto_testable_count": auto_testable_count,
        "confidence_the_champion_survives": float(confidence),
        "overall_assessment": assessment.strip(),
    }


def _prompt_for_contract(contract: str) -> str:
    if contract == "mutator":
        return _mutator_contract_prompt()
    if contract == "judge":
        return _judge_contract_prompt()
    if contract == "committee":
        return _committee_contract_prompt()
    if contract == "inverter":
        return _inverter_contract_prompt()
    return _text_prompt()


def _validate_canary_contract(contract: str, text: str) -> tuple[dict[str, Any], str | None, bool | None]:
    contract_validation: dict[str, Any] = {}
    contract_error: str | None = None
    token_seen = CANARY_TOKEN in text if contract == "text" else None
    try:
        if contract == "mutator":
            contract_validation = _validate_mutator_contract(text)
        elif contract == "judge":
            contract_validation = _validate_judge_contract(text)
        elif contract == "committee":
            contract_validation = _validate_committee_contract(text)
        elif contract == "inverter":
            contract_validation = _validate_inverter_contract(text)
        elif CANARY_TOKEN not in text:
            raise ValueError("expected canary token missing")
    except Exception as exc:
        contract_error = str(exc)
    return contract_validation, contract_error, token_seen


def run_dispatch_canary(
    *,
    call_site: str = "mutator",
    contract: str = "text",
    runtime: str | None = None,
    live: bool = False,
    timeout_seconds: int = 120,
    repo: str | Path = ".",
    full_auto: bool = False,
) -> dict[str, Any]:
    """Exercise ``dispatch_call_text`` through the subscription path.

    The default dry run uses the same dispatch wrapper and scoped env policy,
    but injects a local runner. ``live=True`` invokes the configured
    subscription CLI and validates that a tiny typed response comes back.
    """
    contract = contract.strip().lower()
    if contract not in CANARY_CONTRACTS:
        raise ValueError(f"unsupported canary contract: {contract}")
    runtime = runtime or default_subscription_runtime("ZTARE_AUTORESEARCH_AGENT_RUNTIME")
    site_key = _site_key(call_site)
    env_values = {
        f"ZTARE_AGENT_DISPATCH_{site_key}": "agent",
        f"ZTARE_AUTORESEARCH_{site_key}_AGENT_RUNTIME": runtime,
    }
    if live:
        env_values["ZTARE_LEANMILL_AGENT_FULL_AUTO"] = "1" if full_auto else "0"
    prompt = _prompt_for_contract(contract)
    runner = run_subscription_agent_with_recovery if live else _fake_subscription_runner
    with _temporary_env(env_values):
        response = dispatch_call_text(
            call_site,
            prompt,
            llm_response_call=lambda _prompt: DispatchTextResponse(
                text="api path should not run"
            ),
            backend=runtime,
            repo=repo,
            timeout_seconds=timeout_seconds,
            runner=runner,
        )

    result = response.dispatch_result
    text = response.text or ""
    contract_validation, contract_error, token_seen = _validate_canary_contract(contract, text)
    ok = bool(
        result
        and result.returncode == 0
        and result.transport == "subscription_cli"
        and contract_error is None
    )
    return {
        "schema": "ztare-autoresearch-dispatch-canary-v1",
        "ok": ok,
        "live": live,
        "call_site": call_site,
        "contract": contract,
        "runtime": runtime,
        "capability": result.capability if result else None,
        "transport": result.transport if result else None,
        "worker_archetype": result.worker_archetype if result else None,
        "returncode": result.returncode if result else None,
        "command": list(result.command) if result else [],
        "recovery_note": result.recovery_note if result else None,
        "stdout_excerpt": text[:600],
        "stderr_excerpt": (result.stderr if result else "")[:600],
        "token_seen": token_seen,
        "contract_validation": contract_validation,
        "contract_error": contract_error,
    }


def run_api_canary(
    *,
    call_site: str = "mutator",
    contract: str = "text",
    repo: str | Path = ".",
) -> dict[str, Any]:
    """Exercise the same typed canary through the API/LLM dispatch path.

    This is a dry fixture by design: the ``llm_response_call`` is a local
    deterministic response so the report tests contract parity without spend.
    """

    contract = contract.strip().lower()
    if contract not in CANARY_CONTRACTS:
        raise ValueError(f"unsupported canary contract: {contract}")
    site_key = _site_key(call_site)
    prompt = _prompt_for_contract(contract)
    with _temporary_env({
        "ZTARE_AGENT_DISPATCH": "off",
        f"ZTARE_AGENT_DISPATCH_{site_key}": "off",
    }):
        response = dispatch_call_text(
            call_site,
            prompt,
            llm_response_call=lambda p: DispatchTextResponse(
                text=_mock_response_for_prompt(p),
                model_id_used="fixture-api",
                effective_model_id="fixture-api",
                model_name="fixture-api",
            ),
            repo=repo,
        )

    result = response.dispatch_result
    text = response.text or ""
    contract_validation, contract_error, token_seen = _validate_canary_contract(contract, text)
    ok = bool(
        result
        and result.returncode == 0
        and result.transport == "api"
        and contract_error is None
    )
    return {
        "ok": ok,
        "live": False,
        "call_site": call_site,
        "contract": contract,
        "runtime": "fixture-api",
        "capability": result.capability if result else None,
        "transport": result.transport if result else None,
        "worker_archetype": result.worker_archetype if result else None,
        "returncode": result.returncode if result else None,
        "stdout_excerpt": text[:600],
        "stderr_excerpt": (result.stderr if result else "")[:600],
        "token_seen": token_seen,
        "contract_validation": contract_validation,
        "contract_error": contract_error,
    }


def _fingerprint_validation(contract: str, report: dict[str, Any]) -> Any:
    validation = report.get("contract_validation") or {}
    if contract == "mutator":
        return {
            "mutation_validation": (validation.get("mutation_validation") or {}).get("mismatch_code"),
            "python_code_present": (validation.get("candidate_extraction") or {}).get("python_code_present"),
            "scope_delta": (validation.get("mutation_declaration") or {}).get("scope_delta"),
            "claim_delta_type": (validation.get("mutation_declaration") or {}).get("claim_delta_type"),
        }
    if contract == "judge":
        return {
            "score": validation.get("score"),
            "logic_gap_count": validation.get("logic_gap_count"),
            "probability_dag_keys": validation.get("probability_dag_keys"),
        }
    if contract == "committee":
        return {
            "persona_count": validation.get("persona_count"),
            "roles": validation.get("roles"),
            "focus_areas": validation.get("focus_areas"),
        }
    if contract == "inverter":
        return {
            "test_count": validation.get("test_count"),
            "categories": validation.get("categories"),
            "auto_testable_count": validation.get("auto_testable_count"),
            "confidence_the_champion_survives": validation.get("confidence_the_champion_survives"),
        }
    return {"token_seen": report.get("token_seen")}


def _quality_metrics(contract: str, report: dict[str, Any]) -> dict[str, Any]:
    """Return a small comparable quality surface for a typed canary response.

    This is not a scientific score. It measures whether a worker returned the
    fields that downstream autoresearch code needs before the normal parsers and
    gates can do their work. The metric is deliberately contract-local so live
    subscription runs can be compared to the deterministic replay baseline.
    """

    validation = report.get("contract_validation") or {}
    checks: dict[str, bool] = {}
    if contract == "mutator":
        declaration = validation.get("mutation_declaration") or {}
        extraction = validation.get("candidate_extraction") or {}
        mutation_validation = validation.get("mutation_validation") or {}
        checks = {
            "mutation_contract_clean": mutation_validation.get("mismatch_code") == "CLEAN",
            "python_code_present": extraction.get("python_code_present") is True,
            "scope_delta_present": bool(declaration.get("scope_delta")),
            "claim_delta_present": bool(declaration.get("claim_delta_type")),
        }
    elif contract == "judge":
        checks = {
            "score_numeric": isinstance(validation.get("score"), (int, float)),
            "weakest_point_present": bool(validation.get("weakest_point")),
            "probability_dag_complete": set(validation.get("probability_dag_keys") or [])
            >= {"outcome", "nodes", "edges"},
            "logic_gap_present": int(validation.get("logic_gap_count") or 0) >= 1,
        }
    elif contract == "committee":
        checks = {
            "three_personas": validation.get("persona_count") == 3,
            "roles_present": len(validation.get("roles") or []) == 3,
            "focus_areas_present": len(validation.get("focus_areas") or []) == 3,
        }
    elif contract == "inverter":
        checks = {
            "three_tests": validation.get("test_count") == 3,
            "expected_categories": sorted(validation.get("categories") or [])
            == ["confound", "generalization", "measurement_artifact"],
            "auto_testable_present": int(validation.get("auto_testable_count") or 0) >= 1,
            "survival_confidence_present": isinstance(
                validation.get("confidence_the_champion_survives"),
                (int, float),
            ),
        }
    else:
        checks = {"canary_token_seen": report.get("token_seen") is True}

    passed = sum(1 for value in checks.values() if value)
    total = len(checks)
    return {
        "quality_score": round(passed / total, 4) if total else 0.0,
        "checks_passed": passed,
        "checks_total": total,
        "checks": checks,
    }


def _cost_proxy(report: dict[str, Any], *, elapsed_ms: int) -> dict[str, Any]:
    transport = str(report.get("transport") or "")
    return {
        "elapsed_ms": elapsed_ms,
        "api_model_calls": 1 if transport == "api" else 0,
        "subscription_cli_invocations": 1 if transport == "subscription_cli" else 0,
        "actual_cost_usd": None,
        "cost_basis": "replay_proxy" if not report.get("live") else "live_transport_no_billing_meter",
    }


def run_dispatch_parity_benchmark(
    *,
    contracts: tuple[str, ...] | list[str] = DEFAULT_PARITY_CONTRACTS,
    runtime: str | None = None,
    live_subscription: bool = False,
    timeout_seconds: int = 120,
    repo: str | Path = ".",
    full_auto: bool = False,
) -> dict[str, Any]:
    """Compare API and subscription dispatch on fixed typed canary contracts.

    Default mode is fully local and deterministic. ``live_subscription=True``
    spends subscription runtime only for the subscription leg; the API leg
    remains a fixture so the benchmark isolates transport/contract behavior.
    """

    rows: list[dict[str, Any]] = []
    for raw_contract in contracts:
        contract = raw_contract.strip().lower()
        if not contract:
            continue
        if contract not in CANARY_CONTRACTS:
            raise ValueError(f"unsupported canary contract: {contract}")
        if contract == "judge":
            call_site = "judge"
        elif contract == "committee":
            call_site = "committee"
        elif contract == "inverter":
            call_site = "inverter_review"
        else:
            call_site = "mutator"

        api_start = time.perf_counter()
        api_report = run_api_canary(call_site=call_site, contract=contract, repo=repo)
        api_elapsed_ms = int((time.perf_counter() - api_start) * 1000)

        subscription_start = time.perf_counter()
        subscription_report = run_dispatch_canary(
            call_site=call_site,
            contract=contract,
            runtime=runtime,
            live=live_subscription,
            timeout_seconds=timeout_seconds,
            repo=repo,
            full_auto=full_auto,
        )
        subscription_elapsed_ms = int((time.perf_counter() - subscription_start) * 1000)

        api_fp = _fingerprint_validation(contract, api_report)
        subscription_fp = _fingerprint_validation(contract, subscription_report)
        api_quality = _quality_metrics(contract, api_report)
        subscription_quality = _quality_metrics(contract, subscription_report)
        api_cost_proxy = _cost_proxy(api_report, elapsed_ms=api_elapsed_ms)
        subscription_cost_proxy = _cost_proxy(subscription_report, elapsed_ms=subscription_elapsed_ms)
        contract_parity = (
            api_report.get("ok") is True
            and subscription_report.get("ok") is True
            and api_fp == subscription_fp
        )
        rows.append({
            "contract": contract,
            "call_site": call_site,
            "api": {
                "ok": api_report.get("ok"),
                "transport": api_report.get("transport"),
                "worker_archetype": api_report.get("worker_archetype"),
                "elapsed_ms": api_elapsed_ms,
                "contract_error": api_report.get("contract_error"),
                "validation_fingerprint": api_fp,
                "quality": api_quality,
                "cost_proxy": api_cost_proxy,
            },
            "subscription": {
                "ok": subscription_report.get("ok"),
                "live": subscription_report.get("live"),
                "transport": subscription_report.get("transport"),
                "runtime": subscription_report.get("runtime"),
                "worker_archetype": subscription_report.get("worker_archetype"),
                "elapsed_ms": subscription_elapsed_ms,
                "contract_error": subscription_report.get("contract_error"),
                "validation_fingerprint": subscription_fp,
                "quality": subscription_quality,
                "cost_proxy": subscription_cost_proxy,
            },
            "contract_parity": contract_parity,
            "quality_parity": api_quality["quality_score"] == subscription_quality["quality_score"],
        })

    api_quality_scores = [
        row["api"]["quality"]["quality_score"] for row in rows
    ]
    subscription_quality_scores = [
        row["subscription"]["quality"]["quality_score"] for row in rows
    ]
    return {
        "schema": "ztare-autoresearch-dispatch-parity-v1",
        "ok": bool(rows) and all(row["contract_parity"] for row in rows),
        "live_subscription": live_subscription,
        "runtime": runtime or default_subscription_runtime("ZTARE_AUTORESEARCH_AGENT_RUNTIME"),
        "contracts": [row["contract"] for row in rows],
        "rows": rows,
        "summary": {
            "num_contracts": len(rows),
            "num_parity": sum(1 for row in rows if row["contract_parity"]),
            "api_all_ok": all((row["api"] or {}).get("ok") for row in rows),
            "subscription_all_ok": all((row["subscription"] or {}).get("ok") for row in rows),
            "api_mean_quality_score": (
                round(sum(api_quality_scores) / len(api_quality_scores), 4)
                if api_quality_scores else 0.0
            ),
            "subscription_mean_quality_score": (
                round(sum(subscription_quality_scores) / len(subscription_quality_scores), 4)
                if subscription_quality_scores else 0.0
            ),
            "quality_parity_count": sum(1 for row in rows if row["quality_parity"]),
            "api_total_elapsed_ms": sum(row["api"]["elapsed_ms"] for row in rows),
            "subscription_total_elapsed_ms": sum(row["subscription"]["elapsed_ms"] for row in rows),
            "api_model_calls": sum(row["api"]["cost_proxy"]["api_model_calls"] for row in rows),
            "subscription_cli_invocations": sum(
                row["subscription"]["cost_proxy"]["subscription_cli_invocations"]
                for row in rows
            ),
            "cost_basis": "replay_proxy" if not live_subscription else "live_transport_no_billing_meter",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--call-site", default="mutator")
    parser.add_argument("--contract", default="text", choices=sorted(CANARY_CONTRACTS))
    parser.add_argument(
        "--parity",
        action="store_true",
        help="Run the fixed API-vs-subscription parity benchmark.",
    )
    parser.add_argument(
        "--contracts",
        default=",".join(DEFAULT_PARITY_CONTRACTS),
        help="Comma-separated contracts for --parity (default text,mutator,judge,committee,inverter).",
    )
    parser.add_argument("--runtime", default=None, choices=["codex", "claude"])
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--live", action="store_true", help="Invoke the real subscription CLI.")
    parser.add_argument("--full-auto", action="store_true", help="Allow the runtime's full-auto mode for live canary.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.parity:
        report = run_dispatch_parity_benchmark(
            contracts=tuple(part.strip() for part in args.contracts.split(",")),
            runtime=args.runtime,
            live_subscription=args.live,
            timeout_seconds=args.timeout_seconds,
            repo=args.repo,
            full_auto=args.full_auto,
        )
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(
                "AUTORESEARCH_DISPATCH_PARITY "
                f"status={'ok' if report['ok'] else 'fail'} "
                f"live_subscription={report['live_subscription']} "
                f"runtime={report['runtime']} "
                f"parity={report['summary']['num_parity']}/{report['summary']['num_contracts']}"
            )
            for row in report["rows"]:
                print(
                    f"  - {row['contract']}: parity={row['contract_parity']} "
                    f"api_ok={row['api']['ok']} subscription_ok={row['subscription']['ok']} "
                    f"api_ms={row['api']['elapsed_ms']} subscription_ms={row['subscription']['elapsed_ms']}"
                )
        return 0 if report["ok"] else 1

    report = run_dispatch_canary(
        call_site=args.call_site,
        contract=args.contract,
        runtime=args.runtime,
        live=args.live,
        timeout_seconds=args.timeout_seconds,
        repo=args.repo,
        full_auto=args.full_auto,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            "AUTORESEARCH_DISPATCH_CANARY "
            f"status={'ok' if report['ok'] else 'fail'} "
            f"live={report['live']} call_site={report['call_site']} "
            f"contract={report['contract']} "
            f"runtime={report['runtime']} transport={report['transport']} "
            f"returncode={report['returncode']} token_seen={report['token_seen']}"
        )
        if not report["ok"]:
            print(f"stdout_excerpt={report['stdout_excerpt']!r}")
            print(f"stderr_excerpt={report['stderr_excerpt']!r}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
