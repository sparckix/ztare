"""Mock Wall Harness — GP-078 Composition Mutator isolated test.

Reads a cached structural_memory.json, builds a synthetic FailurePackage,
feeds it to the LLM Composition Mutator, and validates the output compiles
to a valid FitDeclaration.

Usage:
    # Single run (deterministic checks only, no LLM):
    python -m pytest tests/validator/test_mock_wall_harness.py -v

    # Live LLM harness (requires API key, runs N iterations):
    python tests/validator/test_mock_wall_harness.py --live --runs=10

Design:
    - Offline tests (pytest): prompt construction, JSON parsing, compilation
    - Live harness (main): calls the actual LLM, validates parse + compile rate
    - Target: 50 runs in 5 minutes (~6s per call with retries)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Ensure repo root is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ztare.composition.topology_synthesizer import (
    CompositionCommand,
    CompositionMutatorResult,
    CompositionRequest,
    FailurePackage,
    _BASE_PRIMITIVES,
    _parse_composition_response,
    build_composition_prompt,
    build_failure_package,
    compile_composition,
    run_composition_mutator,
)
from src.ztare.composition.structural_memory import StructuralFamilySignature


# ---------------------------------------------------------------------------
# Fixture: synthetic FailurePackage from gp077_a002865_01 structural_memory
# ---------------------------------------------------------------------------

_CACHED_MEMORY_PATH = Path(__file__).resolve().parents[2] / (
    "projects/gp077_a002865_01/workspace/structural_memory.json"
)


def _build_synthetic_failure_package() -> FailurePackage:
    """Build a realistic FailurePackage from cached structural_memory."""
    if _CACHED_MEMORY_PATH.exists():
        memory = json.loads(_CACHED_MEMORY_PATH.read_text(encoding="utf-8"))
        families = memory.get("families", [])
    else:
        families = []

    # Simulate the apex loser — pick the family with lowest residual
    apex = None
    apex_residual = float("inf")
    for fam in families:
        mar = fam.get("best_visible_max_abs_residual")
        if mar is not None and float(mar) < apex_residual:
            apex_residual = float(mar)
            apex = fam

    if apex is None:
        # Fallback: fully synthetic
        apex = {
            "fingerprint": "sfam:synthetic_test",
            "family_label": "P0 * math.sqrt(X0) + P1 * math.log(X0) + P2",
            "example_expression": "A * math.sqrt(n) + B * math.log(n) + C",
            "best_visible_max_abs_residual": 3.14,
        }
        apex_residual = 3.14
        families = [apex]

    # Synthetic residual delta — simulate a periodic + growth pattern
    residual_delta = [
        (float(i), (-1) ** i * (0.5 + 0.1 * i)) for i in range(2, 32)
    ]

    from src.ztare.composition.topology_synthesizer import _compute_residual_statistics

    stats = _compute_residual_statistics(residual_delta)

    return FailurePackage(
        apex_family=StructuralFamilySignature(
            fingerprint=str(apex.get("fingerprint", "")),
            family_label=str(apex.get("family_label", "")),
        ),
        apex_fit={
            "max_abs_residual": apex_residual,
            "expression": apex.get("example_expression", ""),
            "family_label": apex.get("family_label", ""),
        },
        residual_delta=residual_delta,
        residual_statistics=stats,
        exhausted_families=[str(f.get("fingerprint", "")) for f in families],
        holdout_rejection_summary={
            "exact_match_fraction": 0.6,
            "max_abs_residual": apex_residual,
            "gate_result": "REJECT",
        },
        visible_slice_indices=list(range(2, 32)),
    )


# ---------------------------------------------------------------------------
# Offline tests (pytest, no LLM)
# ---------------------------------------------------------------------------


def test_prompt_construction():
    """Prompt builds without error and contains required sections."""
    pkg = _build_synthetic_failure_package()
    prompt = build_composition_prompt(pkg)
    assert "Primitive Library" in prompt
    assert "Exhausted Families" in prompt
    assert "Failure Package" in prompt
    assert "Apex loser" in prompt
    assert pkg.apex_family.family_label in prompt
    assert len(prompt) > 500


def test_parse_valid_nest():
    raw = json.dumps({
        "command": "NEST",
        "operand_a": "sin",
        "operand_b": "log",
        "compose_op": None,
        "motivating_statistic": "sign_change_count",
    })
    result = _parse_composition_response(raw)
    assert isinstance(result, CompositionRequest)
    assert result.command == CompositionCommand.NEST
    assert "math.sin" in result.operand_a
    assert "math.log" in result.operand_b


def test_parse_valid_derive():
    raw = json.dumps({
        "command": "DERIVE",
        "operand_a": "power",
        "operand_b": None,
        "compose_op": None,
        "motivating_statistic": "autocorrelation_lag1",
    })
    result = _parse_composition_response(raw)
    assert isinstance(result, CompositionRequest)
    assert result.command == CompositionCommand.DERIVE
    assert result.operand_b is None


def test_parse_valid_compose():
    raw = json.dumps({
        "command": "COMPOSE",
        "operand_a": "exp",
        "operand_b": "sin",
        "compose_op": "+",
        "motivating_statistic": "mean",
    })
    result = _parse_composition_response(raw)
    assert isinstance(result, CompositionRequest)
    assert result.command == CompositionCommand.COMPOSE
    assert result.compose_op == "+"


def test_parse_strips_markdown_fences():
    raw = "```json\n" + json.dumps({
        "command": "DERIVE",
        "operand_a": "linear",
        "operand_b": None,
        "compose_op": None,
        "motivating_statistic": "autocorrelation_lag1",
    }) + "\n```"
    result = _parse_composition_response(raw)
    assert isinstance(result, CompositionRequest)


def test_parse_rejects_invalid_command():
    raw = json.dumps({"command": "CONVOLVE", "operand_a": "sin", "operand_b": "log"})
    result = _parse_composition_response(raw)
    assert isinstance(result, tuple)
    assert "Invalid command" in result[1]


def test_parse_rejects_unknown_primitive():
    raw = json.dumps({
        "command": "NEST",
        "operand_a": "zeta_function",
        "operand_b": "log",
    })
    result = _parse_composition_response(raw)
    assert isinstance(result, tuple)
    assert "Unknown operand_a" in result[1]


def test_parse_rejects_garbage():
    result = _parse_composition_response("not json at all")
    assert isinstance(result, tuple)
    assert "JSON parse error" in result[1]


def test_compile_nest_passes_ast():
    """NEST(sin, log) should compile and pass AST validation."""
    req = CompositionRequest(
        command=CompositionCommand.NEST,
        operand_a="a * math.sin(b * n + c) + d",
        operand_b="a * math.log(n) + b",
        parameter_names_a=["a", "b", "c", "d"],
        parameter_names_b=["a", "b"],
    )
    result = compile_composition(req)
    assert not isinstance(result, str), f"Compilation failed: {result}"
    assert len(result.parameter_names) == 6
    assert "n" in result.independent_vars


def test_compile_compose_add():
    req = CompositionRequest(
        command=CompositionCommand.COMPOSE,
        operand_a="a * math.sqrt(n) + b",
        operand_b="a * math.exp(b * n) + c",
        compose_op="+",
        parameter_names_a=["a", "b"],
        parameter_names_b=["a", "b", "c"],
    )
    result = compile_composition(req)
    assert not isinstance(result, str), f"Compilation failed: {result}"
    assert len(result.parameter_names) == 5


def test_compile_derive():
    req = CompositionRequest(
        command=CompositionCommand.DERIVE,
        operand_a="a * n**2 + b * n + c",
        parameter_names_a=["a", "b", "c"],
    )
    result = compile_composition(req)
    assert not isinstance(result, str), f"Compilation failed: {result}"
    assert len(result.parameter_names) == 3
    # Forward difference of quadratic should contain (n + 1)
    assert "(n + 1)" in result.expression


def test_all_32_primitives_compile_as_derive():
    """Every base primitive should compile under DERIVE without AST error."""
    for label, expr, params in _BASE_PRIMITIVES:
        req = CompositionRequest(
            command=CompositionCommand.DERIVE,
            operand_a=expr,
            parameter_names_a=params,
        )
        result = compile_composition(req)
        assert not isinstance(result, str), (
            f"DERIVE({label}) failed compilation: {result}"
        )


def test_residual_statistics_periodic():
    """Synthetic periodic residual should produce high sign_change_count."""
    pkg = _build_synthetic_failure_package()
    stats = pkg.residual_statistics
    assert stats["sign_change_count"] > 10  # alternating sign → many changes
    assert stats["sample_n"] == 30


def test_compute_residual_delta_from_fit():
    """Pointwise residual computation from FitSuccess + FitDeclaration."""
    from src.ztare.composition.topology_synthesizer import _compute_residual_delta_from_fit
    from src.ztare.fit.fit_primitive import FitDeclaration, FitSuccess

    decl = FitDeclaration(
        expression="a * n + b",
        independent_vars=["n"],
        parameter_names=["a", "b"],
    )
    fit = FitSuccess(
        fitted_params={"a": 2.0, "b": 1.0},
        max_abs_residual=0.5,
        mean_abs_residual=0.3,
        rmse=0.35,
        residual_map=[],
    )
    # y = 2n + 1 => at n=1, predicted=3; at n=2, predicted=5
    evidence = [(1.0, 3.5), (2.0, 5.0), (3.0, 8.0)]

    residuals = _compute_residual_delta_from_fit(fit, decl, evidence)
    assert len(residuals) == 3
    # n=1: 3.5 - 3.0 = 0.5
    assert abs(residuals[0][1] - 0.5) < 1e-10
    # n=2: 5.0 - 5.0 = 0.0
    assert abs(residuals[1][1] - 0.0) < 1e-10
    # n=3: 8.0 - 7.0 = 1.0
    assert abs(residuals[2][1] - 1.0) < 1e-10


# ---------------------------------------------------------------------------
# Live harness (calls real LLM)
# ---------------------------------------------------------------------------


def _run_live_harness(runs: int, model: str) -> None:
    """Run the composition mutator N times and report success rate."""
    pkg = _build_synthetic_failure_package()

    print(f"\n{'='*60}")
    print(f"Mock Wall Harness — {runs} runs, model={model}")
    print(f"{'='*60}")
    print(f"Apex loser: {pkg.apex_family.family_label}")
    print(f"Residual stats: {json.dumps(pkg.residual_statistics, indent=2)}")
    print(f"Exhausted families: {len(pkg.exhausted_families)}")
    print(f"{'='*60}\n")

    results: list[CompositionMutatorResult] = []
    compile_successes = 0
    parse_successes = 0
    t0 = time.time()

    for i in range(runs):
        t_start = time.time()
        result = run_composition_mutator(
            pkg, model_id=model, retries=2,
        )
        elapsed = time.time() - t_start

        if result.parse_error is None:
            parse_successes += 1
            # Also check compilation
            if result.request is not None:
                compiled = compile_composition(result.request)
                if not isinstance(compiled, str):
                    compile_successes += 1
                    status = "COMPILE_OK"
                else:
                    status = f"COMPILE_FAIL: {compiled[:80]}"
            else:
                status = "PARSE_OK_NO_REQUEST"
        else:
            status = f"PARSE_FAIL: {result.parse_error[:80]}"

        cmd = result.request.command.value if result.request else "?"
        print(f"  [{i+1:3d}/{runs}] {elapsed:5.1f}s  {cmd:8s}  {status}")
        results.append(result)

    total_time = time.time() - t0

    print(f"\n{'='*60}")
    print(f"RESULTS: {runs} runs in {total_time:.1f}s ({total_time/runs:.1f}s/run)")
    print(f"  Parse success:   {parse_successes}/{runs} ({100*parse_successes/runs:.0f}%)")
    print(f"  Compile success: {compile_successes}/{runs} ({100*compile_successes/runs:.0f}%)")

    # Command distribution
    cmd_counts: dict[str, int] = {}
    for r in results:
        if r.request:
            cmd = r.request.command.value
            cmd_counts[cmd] = cmd_counts.get(cmd, 0) + 1
    print(f"  Command distribution: {json.dumps(cmd_counts, indent=4)}")

    # Primitive usage
    a_counts: dict[str, int] = {}
    for r in results:
        if r.request:
            for label, expr, _ in _BASE_PRIMITIVES:
                if r.request.operand_a == expr:
                    a_counts[label] = a_counts.get(label, 0) + 1
                    break
    if a_counts:
        top_a = sorted(a_counts.items(), key=lambda x: -x[1])[:5]
        print(f"  Top operand_a: {top_a}")

    threshold = 0.8
    if compile_successes / runs < threshold:
        print(f"\n  ⚠ BELOW {threshold*100:.0f}% compile threshold — prompt needs work")
    else:
        print(f"\n  Prompt discipline: PASS (>={threshold*100:.0f}% compile rate)")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mock Wall Harness for GP-078")
    parser.add_argument("--live", action="store_true", help="Run live LLM calls")
    parser.add_argument("--runs", type=int, default=10, help="Number of iterations")
    parser.add_argument("--model", type=str, default="gemini-2.5-flash",
                        help="Model ID for the composition mutator")
    args = parser.parse_args()

    if args.live:
        _run_live_harness(args.runs, args.model)
    else:
        print("Run with --live for LLM harness. Use pytest for offline tests.")
        print("  pytest tests/validator/test_mock_wall_harness.py -v")
        print("  python tests/validator/test_mock_wall_harness.py --live --runs=50")
