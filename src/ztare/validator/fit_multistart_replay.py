from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import curve_fit

from src.ztare.common.paths import PROJECTS_DIR
from src.ztare.validator.fit_primitive import (
    FitDeclaration,
    FitSuccess,
    _build_model_callable,
    diagnose_residual_pattern,
    parse_evidence_for_fitting,
)


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _resolve_artifact_paths(project_dir: Path, raw_values: list[str]) -> list[Path]:
    paths: list[Path] = []
    for raw in raw_values:
        candidate = Path(raw)
        if candidate.is_absolute():
            paths.append(candidate)
            continue
        if raw.startswith("projects/"):
            paths.append(Path(raw))
            continue
        paths.append(project_dir / "workspace" / raw)
    return paths


def _build_start_vectors(
    *,
    parameter_names: list[str],
    baseline_params: dict[str, float] | None,
    ydata: np.ndarray,
    starts: int,
    seed: int,
) -> list[tuple[str, list[float]]]:
    rng = np.random.default_rng(seed)
    count = len(parameter_names)
    if count == 0:
        return []

    y_min = float(np.min(ydata))
    y_max = float(np.max(ydata))
    y_span = max(1e-6, y_max - y_min)
    y_scale = max(1e-3, float(np.median(np.abs(ydata))), abs(y_max), abs(y_span))

    vectors: list[tuple[str, list[float]]] = []

    def add(label: str, values: list[float]) -> None:
        if len(vectors) >= starts:
            return
        if any(not np.isfinite(v) for v in values):
            return
        vectors.append((label, values))

    add("ones", [1.0] * count)
    add("tenths", [0.1] * count)
    add("tens", [10.0] * count)
    add("y_scale", [y_scale] * count)
    add("alt_sign_ones", [1.0 if i % 2 == 0 else -1.0 for i in range(count)])

    if baseline_params:
        baseline = [float(baseline_params.get(name, 1.0)) for name in parameter_names]
        add("baseline_fit", baseline)
        for factor in (0.1, 0.3, 3.0, 10.0):
            add(
                f"baseline_scaled_{factor:g}",
                [v * factor if abs(v) > 1e-12 else factor for v in baseline],
            )
        for idx in range(min(8, starts)):
            jitter = 10.0 ** rng.uniform(-1.5, 1.5, size=count)
            signs = rng.choice(np.array([-1.0, 1.0]), size=count, p=[0.25, 0.75])
            values = []
            for base, mag, sign in zip(baseline, jitter, signs):
                if abs(base) < 1e-12:
                    values.append(float(sign * mag))
                else:
                    values.append(float(base * mag * sign))
            add(f"baseline_jitter_{idx+1}", values)

    while len(vectors) < starts:
        magnitudes = 10.0 ** rng.uniform(-2.0, 2.0, size=count)
        signs = rng.choice(np.array([-1.0, 1.0]), size=count, p=[0.35, 0.65])
        values = [float(m * s) for m, s in zip(magnitudes, signs)]
        add(f"generic_{len(vectors)+1}", values)

    return vectors[:starts]


def _fit_once(
    declaration: FitDeclaration,
    xdata: np.ndarray,
    ydata: np.ndarray,
    *,
    p0: list[float],
    maxfev: int,
) -> FitSuccess:
    model_fn = _build_model_callable(declaration)
    lo = [
        declaration.bounds.get(name, (-np.inf, np.inf))[0]
        for name in declaration.parameter_names
    ]
    hi = [
        declaration.bounds.get(name, (-np.inf, np.inf))[1]
        for name in declaration.parameter_names
    ]
    popt, _ = curve_fit(
        model_fn,
        xdata,
        ydata,
        p0=p0,
        bounds=(lo, hi),
        maxfev=maxfev,
    )
    y_pred = model_fn(xdata, *popt)
    residuals = np.abs(ydata - y_pred)
    if xdata.ndim == 1:
        x_for_map = xdata.reshape(1, -1)
    else:
        x_for_map = xdata
    residual_map: list[dict[str, float]] = []
    for i in range(len(ydata)):
        pt: dict[str, float] = {}
        for j, vname in enumerate(declaration.independent_vars):
            pt[vname] = float(x_for_map[j, i])
        pt["observed"] = float(ydata[i])
        pt["predicted"] = float(y_pred[i])
        pt["residual"] = float(residuals[i])
        residual_map.append(pt)
    return FitSuccess(
        fitted_params={
            name: float(val) for name, val in zip(declaration.parameter_names, popt)
        },
        max_abs_residual=float(np.max(residuals)),
        mean_abs_residual=float(np.mean(residuals)),
        rmse=float(np.sqrt(np.mean(residuals**2))),
        residual_map=residual_map,
    )


def replay_multistart_for_artifact(
    *,
    artifact_path: Path,
    evidence_text: str,
    starts: int,
    seed: int,
    maxfev: int,
    gate_threshold: float,
) -> dict[str, Any]:
    payload = json.loads(artifact_path.read_text())
    if payload.get("status") != "success":
        return {
            "artifact": str(artifact_path),
            "status": "skipped",
            "reason": f"artifact status is {payload.get('status')!r}",
        }

    declaration = FitDeclaration(
        expression=str(payload["expression"]),
        independent_vars=list(payload["independent_vars"]),
        parameter_names=list(payload["parameter_names"]),
        initial_guesses={},
        bounds={},
    )
    parsed = parse_evidence_for_fitting(evidence_text, declaration.independent_vars)
    if parsed is None:
        return {
            "artifact": str(artifact_path),
            "status": "error",
            "reason": "Could not parse visible evidence for declared independent vars.",
        }
    xdata_lists, ydata_list = parsed
    xdata = np.array(xdata_lists)
    ydata = np.array(ydata_list)

    baseline_params = payload.get("fitted_params", {})
    starts_list = _build_start_vectors(
        parameter_names=declaration.parameter_names,
        baseline_params=baseline_params if isinstance(baseline_params, dict) else None,
        ydata=ydata,
        starts=starts,
        seed=seed,
    )

    failures: Counter[str] = Counter()
    successes: list[dict[str, Any]] = []
    for label, p0 in starts_list:
        try:
            result = _fit_once(
                declaration,
                xdata,
                ydata,
                p0=p0,
                maxfev=maxfev,
            )
            successes.append(
                {
                    "start_label": label,
                    "initial_guess": {
                        name: float(val)
                        for name, val in zip(declaration.parameter_names, p0)
                    },
                    "result": result,
                }
            )
        except Exception as exc:
            failures[type(exc).__name__] += 1

    if not successes:
        return {
            "artifact": str(artifact_path),
            "status": "all_failed",
            "expression": declaration.expression,
            "successful_starts": 0,
            "failed_starts": len(starts_list),
            "failure_classes": dict(failures),
        }

    successes.sort(
        key=lambda item: (
            item["result"].max_abs_residual,
            item["result"].rmse,
        )
    )
    best = successes[0]
    best_result: FitSuccess = best["result"]
    baseline_max = float(payload.get("max_abs_residual", float("inf")))
    best_diag = diagnose_residual_pattern(best_result, declaration.independent_vars)
    top_results = []
    for item in successes[:5]:
        result: FitSuccess = item["result"]
        top_results.append(
            {
                "start_label": item["start_label"],
                "max_abs_residual": result.max_abs_residual,
                "mean_abs_residual": result.mean_abs_residual,
                "rmse": result.rmse,
            }
        )

    return {
        "artifact": str(artifact_path),
        "status": "ok",
        "expression": declaration.expression,
        "baseline_max_abs_residual": baseline_max,
        "best_max_abs_residual": best_result.max_abs_residual,
        "best_mean_abs_residual": best_result.mean_abs_residual,
        "best_rmse": best_result.rmse,
        "improved": bool(best_result.max_abs_residual < baseline_max),
        "passed_gate_threshold": bool(best_result.max_abs_residual < gate_threshold),
        "successful_starts": len(successes),
        "failed_starts": len(starts_list) - len(successes),
        "failure_classes": dict(failures),
        "best_start_label": best["start_label"],
        "best_initial_guess": best["initial_guess"],
        "best_fitted_params": best_result.fitted_params,
        "best_residual_diagnostic": asdict(best_diag),
        "top_results": top_results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline multistart replay for GP-041 form-family escape ablations."
    )
    parser.add_argument("--project", required=True)
    parser.add_argument(
        "--fit-artifact",
        action="append",
        dest="fit_artifacts",
        required=True,
        help="Workspace fit artifact filename, repo-relative path, or absolute path. Repeatable.",
    )
    parser.add_argument("--starts", type=int, default=64)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--maxfev", type=int, default=40000)
    parser.add_argument("--gate-threshold", type=float, default=0.05)
    args = parser.parse_args()

    project_dir = PROJECTS_DIR / args.project
    workspace_dir = project_dir / "workspace"
    evidence_path = project_dir / "evidence.txt"
    if not evidence_path.exists():
        raise SystemExit(f"Missing evidence file: {evidence_path}")
    evidence_text = evidence_path.read_text()

    artifacts = _resolve_artifact_paths(project_dir, args.fit_artifacts)
    results = []
    for artifact_path in artifacts:
        results.append(
            replay_multistart_for_artifact(
                artifact_path=artifact_path,
                evidence_text=evidence_text,
                starts=args.starts,
                seed=args.seed,
                maxfev=args.maxfev,
                gate_threshold=args.gate_threshold,
            )
        )

    summary = {
        "project": args.project,
        "generated_on": _utc_now_iso(),
        "starts_per_candidate": args.starts,
        "seed": args.seed,
        "maxfev": args.maxfev,
        "gate_threshold": args.gate_threshold,
        "results": results,
    }

    output_path = workspace_dir / "multistart_replay_summary.json"
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
