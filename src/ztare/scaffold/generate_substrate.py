"""GP-072 Phase 2 — Automated substrate generator (Division A).

Takes a Ground Truth specification and generates all experiment artifacts
with proper Division A/B information isolation.

Division A artifacts (GT-aware, not mutator-visible):
  - substrate_gt.py          (f_true, f_dominant)
  - evidence_holdout.txt     (holdout triples)
  - .denylist                (GT-specific leak patterns)

Division B artifacts (GT-blind, mutator-visible):
  - evidence.txt             (visible triples)
  - gate_harness.py          (frozen evaluator)
  - test_model.py            (trivial baseline)
  - thesis.md                (neutral seed)
  - project_charter.md       (neutral problem statement)

Usage:
    python -m src.ztare.scaffold.generate_substrate \\
        --slug my_experiment \\
        --gt-expr "u**2 * v - u + round(0.08 * v)" \\
        --dominant-expr "u**2 * v - u" \\
        --variables u,v \\
        --visible-ranges "u:1:5,v:1:15" \\
        --holdout-ranges "u:1:5,v:16:25" \\
        --problem-brief "integer-valued function of two variables" \\
        --denylist "0.08,round(0.08,1/12,0.083"

The GT expression is used ONLY for Division A artifacts. Division B
artifacts never contain the expression or any derivative of it.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import textwrap
import time
from pathlib import Path


PROJECTS_DIR = Path("projects")
RUBRICS_DIR = Path("rubrics")
SUBSTRATES_DIR = Path("src/ztare/substrates")


def _parse_ranges(spec: str) -> dict[str, tuple[float, float]]:
    """Parse 'u:1:5,v:1:15' or 't:0.001:1.0' into {'u': (1, 5), ...}.

    Accepts both integer and float bounds — continuous substrates use float.
    Callers that iterate over integer grids must cast to int themselves.
    """
    result = {}
    for part in spec.split(","):
        tokens = part.strip().split(":")
        if len(tokens) != 3:
            raise ValueError(f"Bad range spec: {part!r}, expected var:lo:hi")
        name = tokens[0].strip()
        try:
            lo: float = int(tokens[1])
            hi: float = int(tokens[2])
        except ValueError:
            lo = float(tokens[1])
            hi = float(tokens[2])
        result[name] = (lo, hi)
    return result


def _build_gt_function(expr: str, variables: list[str]) -> callable:
    """Build a callable from a GT expression string."""
    allowed_names = {
        "round": round, "abs": abs, "max": max, "min": min,
        "math": math, "int": int, "float": float,
    }
    for v in variables:
        allowed_names[v] = None

    def f(**kwargs):
        ns = dict(allowed_names)
        ns.update(kwargs)
        return int(eval(expr, {"__builtins__": {}}, ns))
    return f


def _load_gt_script(script_path: str, variables: list[str]) -> tuple[callable, object]:
    """Load a GT function from a Python script file (recurrence support).

    The script must export ``f_true(n)`` (1-variable) or ``f_true(x1, x2)``
    (2-variable).  This allows recurrences and other non-expression GTs.

    Returns (f_callable, gt_module) so callers can inspect evidence_grid() /
    holdout_grid() for continuous substrates.

    For discrete substrates the callable casts to int (existing behaviour).
    For continuous substrates (gt_module exposes evidence_grid()), the caller
    bypasses _generate_triples entirely and uses the explicit grid.
    """
    import importlib.util as ilu
    spec = ilu.spec_from_file_location("_gt_script", script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load GT script: {script_path}")
    mod = ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "f_true"):
        raise AttributeError(f"GT script {script_path} must export f_true()")
    raw_fn = mod.f_true
    continuous = hasattr(mod, "evidence_grid")

    def f(**kwargs):
        args = [kwargs[v] for v in variables]
        result = raw_fn(*args)
        return result if continuous else int(result)

    return f, mod


def _generate_triples_from_grid(
    f: callable,
    grid: list[tuple],
    variables: list[str],
) -> list[tuple]:
    """Generate (x1, x2, ..., z) triples from an explicit point grid (continuous substrates).

    Unlike _generate_triples, this does NOT cast z to int — preserves float precision.
    """
    triples = []
    for point in grid:
        kwargs = {v: point[i] for i, v in enumerate(variables)}
        z = f(**kwargs)
        triples.append((*point, z))
    return triples


def _apply_transform(z: int, transform: str | None, scale: int = 1000) -> int:
    """Apply an optional evidence transform (GP-077: log-space for exponential sequences)."""
    if not transform:
        return z
    if transform == "log":
        if z <= 0:
            return 0
        return round(scale * math.log(z))
    if transform == "log10":
        if z <= 0:
            return 0
        return round(scale * math.log10(z))
    raise ValueError(f"Unknown transform: {transform!r}")


def _generate_triples(
    f: callable,
    ranges: dict[str, tuple[int, int]],
    variables: list[str],
    transform: str | None = None,
    transform_scale: int = 1000,
) -> list[tuple]:
    """Generate all (var1, var2, ..., z) triples from ranges."""
    if len(variables) == 1:
        v0 = variables[0]
        lo, hi = ranges[v0]
        triples = []
        for a in range(lo, hi + 1):
            z = f(**{v0: a})
            z = _apply_transform(z, transform, transform_scale)
            triples.append((a, z))
        return triples
    if len(variables) == 2:
        v0, v1 = variables
        lo0, hi0 = ranges[v0]
        lo1, hi1 = ranges[v1]
        triples = []
        for a in range(lo0, hi0 + 1):
            for b in range(lo1, hi1 + 1):
                z = f(**{v0: a, v1: b})
                z = _apply_transform(z, transform, transform_scale)
                triples.append((a, b, z))
        return triples
    raise NotImplementedError("Only 1- and 2-variable substrates supported")


def _write_evidence(path: Path, triples: list[tuple], variables: list[str], header: str):
    """Write evidence file with tab-separated triples."""
    lines = [f"# {header}"]
    lines.append("# " + "\t".join(variables + ["z"]))
    for triple in triples:
        lines.append("\t".join(str(x) for x in triple))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_gt_module(
    path: Path,
    gt_expr: str,
    dominant_expr: str,
    variables: list[str],
    continuous: bool = False,
):
    """Write the substrate GT module (Division A artifact).

    continuous=True: uses float type hints and omits int() casts.
    """
    if continuous:
        var_sig = ", ".join(f"{v}: float" for v in variables)
        ret_type = "float"
        cast = ""
    else:
        var_sig = ", ".join(f"{v}: int" for v in variables)
        ret_type = "int"
        cast = "int"
    var_call = ", ".join(variables)
    lines = [
        '"""Ground-truth module (Division A artifact — not mutator-visible).',
        "",
        f"GT: f({var_call}) = {gt_expr}",
        f"Dominant: {dominant_expr}",
        '"""',
        "from __future__ import annotations",
        "",
        "import math",
        "",
        "",
        f"def f_true({var_sig}) -> {ret_type}:",
        f"    return {cast + '(' if cast else ''}{gt_expr}{')' if cast else ''}",
        "",
        "",
        f"def f_dominant({var_sig}) -> {ret_type}:",
        f"    return {cast + '(' if cast else ''}{dominant_expr}{')' if cast else ''}",
        "",
        "",
        'if __name__ == "__main__":',
        '    print("GT module verification")',
    ]
    if len(variables) == 1:
        v0 = variables[0]
        lines += [
            f"    for {v0} in range(1, 20):",
            f"        ft = f_true({v0})",
            f"        fd = f_dominant({v0})",
            f'        print(f"  {v0}={{{v0}}}: f_true={{ft}}, f_dominant={{fd}}, diff={{ft-fd}}")',
        ]
    else:
        v0, v1 = variables[0], variables[1]
        lines += [
            f"    for {v0} in [1, 3, 5]:",
            f"        for {v1} in [1, 5, 10]:",
            f"            ft = f_true({v0}, {v1})",
            f"            fd = f_dominant({v0}, {v1})",
            f'            print(f"  {v0}={{{v0}}}, {v1}={{{v1}}}: f_true={{ft}}, f_dominant={{fd}}, diff={{ft-fd}}")',
        ]
    content = "\n".join(lines) + "\n"
    path.write_text(content, encoding="utf-8")


def _write_gt_stub(path: Path, gt_script: str):
    """Write an opaque re-export stub at the slug path when --gt-script is used.

    Keeps the rubric pointing to the slug-named module (Division B-safe) while
    actual GT parameters live in the Division A script.  Never overwrites an
    existing stub so repeated generate_substrate calls are idempotent.
    """
    gt_script_path = Path(gt_script).resolve()
    # Derive the Python module dotted path from the file path relative to repo root.
    # Fall back to absolute import if path doesn't fit under src/.
    try:
        rel = gt_script_path.relative_to(Path.cwd())
        module_path = str(rel).replace("/", ".").removesuffix(".py")
    except ValueError:
        module_path = gt_script_path.stem

    content = (
        f'"""GT module stub — re-exports from {module_path} (Division A artifact).\n\n'
        f"Opaque slug name. Rubric points here; GT parameters live in {module_path}.\n"
        f'Do not add domain hints or parameter values to this file.\n"""\n'
        f"from {module_path} import *  # noqa: F401, F403\n"
    )
    path.write_text(content, encoding="utf-8")


def _write_gate_harness_1var(project_dir: Path, var_name: str):
    """Write a 1-variable gate harness (reads 2-column evidence, calls f(n))."""
    content = textwrap.dedent(f'''\
        """Frozen deterministic-gate harness (auto-generated by generate_substrate).

        1-variable substrate: imports f from test_model.py, evaluates against holdout.
        Scoring: integer exact-match.
        """
        from __future__ import annotations

        import importlib.util
        import json
        import os
        import sys

        _DIR = os.path.dirname(os.path.realpath(__file__))


        def _load_evidence(path: str) -> list[tuple[int, int]]:
            pairs = []
            with open(path) as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split()
                    pairs.append((int(parts[0]), int(parts[1])))
            return pairs


        def _evaluate(f_model, pairs):
            matches = 0
            total = len(pairs)
            errors = []
            for {var_name}, expected in pairs:
                try:
                    predicted = int(f_model({var_name}))
                except Exception:
                    predicted = None
                if predicted == expected:
                    matches += 1
                else:
                    errors.append({{"n": {var_name}, "expected": expected, "predicted": predicted}})
            frac = matches / total if total > 0 else 0.0
            return {{
                "exact_match": frac,
                "matches": matches,
                "total": total,
                "errors": errors[:5],
            }}


        def _load_f_model():
            test_model_path = os.path.join(_DIR, "test_model.py")
            spec = importlib.util.spec_from_file_location("_test_model", test_model_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "f"):
                return mod.f
            raise AttributeError("test_model.py does not expose f()")


        def main(argv):
            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("--run-visible-assertions", action="store_true")
            parser.add_argument("--emit-deterministic-gates", action="store_true")
            parser.add_argument("--run-smoke-test", action="store_true")
            parser.add_argument("--eval_results_path", default=None)
            parser.add_argument("--rubric", default=None)
            parser.add_argument("--project", default=None)
            parser.add_argument("--judge_model", default=None)
            parser.add_argument("--mutator_model", default=None)
            parser.add_argument("--deterministic_score_gates", action="store_true")
            parser.add_argument("--disable_attacker_tools", action="store_true")
            args = parser.parse_args(argv)

            f_fn = _load_f_model()
            holdout = _load_evidence(os.path.join(_DIR, "evidence_holdout.txt"))

            if args.run_smoke_test:
                visible = _load_evidence(os.path.join(_DIR, "evidence.txt"))
                print(f"smoke-test: {{len(visible)}} visible, {{len(holdout)}} holdout pairs")
                r = _evaluate(f_fn, holdout)
                print(f"  score={{r['matches']}}/{{r['total']}}, exact_match={{r['exact_match']}}")
                print("smoke-test: PASSED")
                return 0

            if args.emit_deterministic_gates:
                r = _evaluate(f_fn, holdout)
                gates = [
                    {{
                        "name": "holdout_exact_match",
                        "value": r["exact_match"],
                        "threshold": 1.0,
                        "operator": ">=",
                        "passed": r["exact_match"] >= 1.0,
                    }},
                ]
                print(json.dumps({{
                    "gates": gates,
                    "harness_ok": all(g["passed"] for g in gates),
                    "exact_match_fraction": r["exact_match"],
                    "mismatches": r.get("errors", [])[:5],
                }}))
                return 0

            if args.run_visible_assertions:
                visible = _load_evidence(os.path.join(_DIR, "evidence.txt"))
                r = _evaluate(f_fn, visible)
                print(json.dumps(r, indent=2))
                if r["exact_match"] == 1.0:
                    return 0
                # GP-135 fix (2026-04-23): emit AssertionError to stderr so
                # classify_harness_failure() treats this as fail_assert (real
                # falsification), not fail_other (harness defect). Silent exit
                # 1 was being misread as a broken harness, capping scores and
                # firing the holdout hard-gate erroneously.
                import sys as _s
                miss = r.get("errors", [])[:5]
                _s.stderr.write(
                    "AssertionError: visible exact_match_fraction="
                    + str(r["exact_match"])
                    + " < 1.0; first mismatches: "
                    + str(miss)
                )
                return 1

            if args.eval_results_path:
                import time
                from pathlib import Path
                r = _evaluate(f_fn, holdout)
                visible = _load_evidence(os.path.join(_DIR, "evidence.txt"))
                vr = _evaluate(f_fn, visible)
                output = {{
                    "generated_on": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "score": int(r["exact_match"] * 100),
                    "weakest_point": "all holdout points matched exactly" if r["exact_match"] == 1.0 else f"{{len(r['errors'])}} holdout mismatches",
                    "score_contract": {{
                        "mode": "integer_exact_match",
                        "exact_match_fraction": r["exact_match"],
                        "visible_exact_match": vr["exact_match"],
                        "holdout_hard_gate_passed": r["exact_match"] >= 1.0,
                    }},
                }}
                Path(args.eval_results_path).write_text(json.dumps(output, indent=2))
                return 0

            r = _evaluate(f_fn, holdout)
            print(json.dumps(r, indent=2))
            return 0 if r["exact_match"] == 1.0 else 1


        if __name__ == "__main__":
            sys.exit(main(sys.argv[1:]))
    ''')
    (project_dir / "gate_harness.py").write_text(content, encoding="utf-8")


def _write_gate_harness_continuous_1var(project_dir: Path, var_name: str, rmse_threshold: float = 2.0):
    """Write a 1-variable continuous gate harness (2-column float evidence, normalised RMSE gate)."""
    content = textwrap.dedent(f'''\
        """Frozen deterministic-gate harness (auto-generated by generate_substrate).

        1-variable continuous substrate: reads float pairs, evaluates normalised RMSE against holdout.
        Gate: nRMSE < {rmse_threshold:.4f} (set at generation time).
        """
        from __future__ import annotations

        import importlib.util
        import json
        import math
        import sys
        from pathlib import Path

        _PROJECT_DIR = Path(__file__).resolve().parent
        _VISIBLE_PATH = _PROJECT_DIR / "evidence.txt"
        _HOLDOUT_PATH = _PROJECT_DIR / "evidence_holdout.txt"
        _NRMSE_THRESHOLD = {rmse_threshold}


        def _parse_pairs(path: Path) -> list[tuple[float, float]]:
            pairs = []
            for raw in path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\\t") if "\\t" in line else line.split()
                if len(parts) < 2:
                    continue
                try:
                    pairs.append((float(parts[0]), float(parts[1])))
                except ValueError:
                    continue
            return pairs


        def _load_model():
            test_model_path = _PROJECT_DIR / "test_model.py"
            spec = importlib.util.spec_from_file_location("_test_model", str(test_model_path))
            if spec is None or spec.loader is None:
                raise ImportError(f"cannot build spec for {{test_model_path}}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if not hasattr(module, "f"):
                raise AttributeError("test_model.py must expose f({var_name}) -> float")
            return module.f


        def _safe_call(f_fn, {var_name}: float):
            try:
                v = float(f_fn({var_name}))
                return v if math.isfinite(v) else None
            except Exception:
                return None


        def _normalised_rmse(f_fn, pairs):
            sq_errs = []
            for {var_name}, z_obs in pairs:
                pred = _safe_call(f_fn, {var_name})
                if pred is None or z_obs == 0.0:
                    sq_errs.append(1.0)
                else:
                    sq_errs.append(((pred - z_obs) / z_obs) ** 2)
            if not sq_errs:
                return float("inf")
            return math.sqrt(sum(sq_errs) / len(sq_errs))


        def _evaluate(f_fn) -> dict:
            holdout = _parse_pairs(_HOLDOUT_PATH)
            nrmse = _normalised_rmse(f_fn, holdout)
            passed = nrmse < _NRMSE_THRESHOLD
            return {{
                "harness_ok": passed,
                "harness_invoked": True,
                "nrmse": round(nrmse, 6) if math.isfinite(nrmse) else None,
                "nrmse_threshold": _NRMSE_THRESHOLD,
                "n_holdout": len(holdout),
                "gates": [{{
                    "id": "HOLDOUT_NRMSE",
                    "passed": passed,
                    "actual": round(nrmse, 6) if math.isfinite(nrmse) else None,
                    "threshold": _NRMSE_THRESHOLD,
                    "description": f"Normalised RMSE on holdout < {{_NRMSE_THRESHOLD}}",
                }}],
            }}


        def _run_visible_assertions(f_fn) -> int:
            pairs = _parse_pairs(_VISIBLE_PATH)
            failures = [x for x, _ in pairs if _safe_call(f_fn, x) is None]
            if failures:
                raise AssertionError(
                    f"Model returned NaN/inf or crashed on {{len(failures)}} visible point(s)"
                )
            print(f"Visible structural check: all {{len(pairs)}} points finite.")
            return 0


        def main() -> None:
            args = sys.argv[1:]
            f_fn = _load_model()

            if "--run-smoke-test" in args:
                vis = _parse_pairs(_VISIBLE_PATH)
                r = _evaluate(f_fn)
                print(f"smoke-test: {{len(vis)}} visible, {{r['n_holdout']}} holdout pairs")
                print(f"  nrmse={{r['nrmse']}}, threshold={{_NRMSE_THRESHOLD}}, passed={{r['harness_ok']}}")
                print("smoke-test: PASSED (harness_invoked)")
                sys.exit(0)

            if "--run-visible-assertions" in args:
                sys.exit(_run_visible_assertions(f_fn))

            if "--emit-deterministic-gates" in args:
                r = _evaluate(f_fn)
                print(json.dumps(r, indent=2))
                sys.exit(0 if r["harness_invoked"] else 1)

            # Default: full evaluation
            r = _evaluate(f_fn)
            print(json.dumps(r, indent=2))
            sys.exit(0 if r["harness_ok"] else 1)


        if __name__ == "__main__":
            main()
    ''')
    (project_dir / "gate_harness.py").write_text(content, encoding="utf-8")


def _write_gate_harness_continuous(project_dir: Path, variables: list[str], rmse_threshold: float = 2.0):
    """Write a continuous-valued gate harness (float evidence, RMSE gate).

    Used for substrates where z is a float (e.g. concentration, temperature).
    Scoring: RMSE < threshold (not exact integer match).
    Supports both 1-variable (t, z) and 2-variable (x1, x2, z) evidence files.
    """
    if len(variables) < 1:
        raise ValueError("continuous harness requires at least 1 variable")
    if len(variables) == 1:
        _write_gate_harness_continuous_1var(project_dir, variables[0], rmse_threshold)
        return
    v0, v1 = variables[0], variables[1]
    content = textwrap.dedent(f'''\
        """Frozen deterministic-gate harness (auto-generated by generate_substrate).

        Continuous substrate: reads float triples, evaluates RMSE against holdout.
        Gate: RMSE < {rmse_threshold:.4f} (set at generation time).
        """
        from __future__ import annotations

        import argparse
        import importlib.util
        import json
        import math
        import sys
        from pathlib import Path

        _PROJECT_DIR = Path(__file__).resolve().parent
        _VISIBLE_PATH = _PROJECT_DIR / "evidence.txt"
        _HOLDOUT_PATH = _PROJECT_DIR / "evidence_holdout.txt"
        _RMSE_THRESHOLD = {rmse_threshold}


        def _parse_triples(path: Path) -> list[tuple[float, float, float]]:
            triples = []
            for raw in path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\\t") if "\\t" in line else line.split()
                if len(parts) < 3:
                    continue
                try:
                    triples.append((float(parts[0]), float(parts[1]), float(parts[2])))
                except ValueError:
                    continue
            return triples


        def _load_model():
            test_model_path = _PROJECT_DIR / "test_model.py"
            spec = importlib.util.spec_from_file_location("_test_model", str(test_model_path))
            if spec is None or spec.loader is None:
                raise ImportError(f"cannot build spec for {{test_model_path}}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if not hasattr(module, "f"):
                raise AttributeError("test_model.py does not expose f()")
            return module.f


        def _safe_call(f_fn, {v0}, {v1}):
            try:
                return float(f_fn({v0}, {v1}))
            except Exception:
                return None


        def _evaluate(f_fn, triples):
            sq_errors = []
            max_abs = 0.0
            mismatches = []
            for {v0}, {v1}, z in triples:
                pred = _safe_call(f_fn, {v0}, {v1})
                if pred is None:
                    mismatches.append({{"x1": {v0}, "x2": {v1}, "expected": z, "predicted": None}})
                    sq_errors.append(z ** 2)
                else:
                    err = pred - z
                    sq_errors.append(err ** 2)
                    abs_err = abs(err)
                    if abs_err > max_abs:
                        max_abs = abs_err
                    if abs_err > _RMSE_THRESHOLD:
                        mismatches.append({{"x1": {v0}, "x2": {v1}, "expected": z, "predicted": pred, "abs_err": abs_err}})
            rmse = math.sqrt(sum(sq_errors) / len(sq_errors)) if sq_errors else 0.0
            passed = rmse < _RMSE_THRESHOLD
            return {{
                "harness_ok": passed,
                "rmse": rmse,
                "rmse_threshold": _RMSE_THRESHOLD,
                "score": max(0, int(100 * (1.0 - rmse / (_RMSE_THRESHOLD * 2)))),
                "max_abs_residual": max_abs,
                "n_points": len(triples),
                "mismatches": mismatches[:5],
            }}


        def main(argv):
            parser = argparse.ArgumentParser()
            parser.add_argument("--run-visible-assertions", action="store_true")
            parser.add_argument("--emit-deterministic-gates", action="store_true")
            parser.add_argument("--run-smoke-test", action="store_true")
            parser.add_argument("--eval_results_path", default=None)
            parser.add_argument("--rubric", default=None)
            parser.add_argument("--project", default=None)
            parser.add_argument("--judge_model", default=None)
            parser.add_argument("--mutator_model", default=None)
            parser.add_argument("--deterministic_score_gates", action="store_true")
            parser.add_argument("--disable_attacker_tools", action="store_true")
            args = parser.parse_args(argv)

            f_fn = _load_model()

            if args.run_visible_assertions or args.run_smoke_test:
                vis = _parse_triples(_VISIBLE_PATH)
                vis_result = _evaluate(f_fn, vis)
                if args.run_smoke_test:
                    print(json.dumps({{"smoke_test": "visible", **vis_result}}, indent=2))

            if args.emit_deterministic_gates:
                holdout = _parse_triples(_HOLDOUT_PATH)
                result = _evaluate(f_fn, holdout)
                print(json.dumps(result, indent=2))
                if not result["harness_ok"]:
                    sys.exit(1)


        if __name__ == "__main__":
            main(sys.argv[1:])
    ''')
    (project_dir / "gate_harness.py").write_text(content, encoding="utf-8")


def _write_gate_harness(project_dir: Path, variables: list[str] | None = None, continuous: bool = False):
    """Write the frozen gate harness (Division B artifact).

    When *variables* has length 1, emits a 1-variable harness that reads
    two-column evidence files and calls ``f(n)``.
    When *continuous* is True, emits a float RMSE harness instead of integer exact-match.
    Otherwise emits the original 2-variable integer harness.
    """
    if variables is not None and len(variables) == 1:
        _write_gate_harness_1var(project_dir, variables[0])
        return
    if continuous:
        _write_gate_harness_continuous(project_dir, variables or ["x1", "x2"])
        return
    content = textwrap.dedent('''\
        """Frozen deterministic-gate harness (auto-generated by generate_substrate).

        Imports f from test_model.py, evaluates against holdout evidence.
        Scoring: integer exact-match.
        """
        from __future__ import annotations

        import argparse
        import importlib.util
        import json
        import sys
        import time
        from pathlib import Path

        _PROJECT_DIR = Path(__file__).resolve().parent
        _VISIBLE_PATH = _PROJECT_DIR / "evidence.txt"
        _HOLDOUT_PATH = _PROJECT_DIR / "evidence_holdout.txt"


        def _parse_triples(path: Path) -> list[tuple[int, int, int]]:
            triples: list[tuple[int, int, int]] = []
            for raw in path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\\t") if "\\t" in line else line.split()
                if len(parts) < 3:
                    continue
                try:
                    triples.append(tuple(int(x) for x in parts[:3]))
                except ValueError:
                    continue
            return triples


        def _load_model():
            test_model_path = _PROJECT_DIR / "test_model.py"
            spec = importlib.util.spec_from_file_location("_test_model", str(test_model_path))
            if spec is None or spec.loader is None:
                raise ImportError(f"cannot build spec for {test_model_path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if not hasattr(module, "f"):
                raise AttributeError("test_model.py does not expose f()")
            return module.f


        def _safe_call(f_fn, u: int, v: int) -> int | None:
            try:
                return int(f_fn(u, v))
            except Exception:
                return None


        def _evaluate(f_fn, triples):
            matches, max_res, worst, worst_res = 0, 0, None, 0
            mismatches = []
            for u, v, z in triples:
                pred = _safe_call(f_fn, u, v)
                if pred is None:
                    mismatches.append({"u": u, "v": v, "expected": z, "predicted": None})
                    r = abs(z)
                elif pred == z:
                    matches += 1
                    r = 0
                else:
                    r = abs(pred - z)
                    mismatches.append({"u": u, "v": v, "expected": z, "predicted": pred, "residual": r})
                if r > max_res:
                    max_res = r
                if r > worst_res:
                    worst_res, worst = r, (u, v, z, pred)
            frac = matches / len(triples) if triples else 0.0
            if worst:
                wp = f"f({worst[0]},{worst[1]})={worst[3]}, expected {worst[2]}, residual={worst_res}"
            elif frac == 1.0:
                wp = "all holdout points matched exactly"
            else:
                wp = "no triples"
            return {
                "harness_ok": frac == 1.0,
                "exact_match_fraction": frac,
                "score": int(frac * 100),
                "max_abs_residual": max_res,
                "weakest_point": wp,
                "mismatches": mismatches,
            }


        def main(argv):
            parser = argparse.ArgumentParser()
            parser.add_argument("--run-visible-assertions", action="store_true")
            parser.add_argument("--emit-deterministic-gates", action="store_true")
            parser.add_argument("--run-smoke-test", action="store_true")
            parser.add_argument("--eval_results_path", default=None)
            parser.add_argument("--rubric", default=None)
            parser.add_argument("--project", default=None)
            parser.add_argument("--judge_model", default=None)
            parser.add_argument("--mutator_model", default=None)
            parser.add_argument("--deterministic_score_gates", action="store_true")
            parser.add_argument("--disable_attacker_tools", action="store_true")
            args = parser.parse_args(argv)

            f_fn = _load_model()
            visible = _parse_triples(_VISIBLE_PATH)
            holdout = _parse_triples(_HOLDOUT_PATH)

            if args.run_smoke_test:
                print(f"smoke-test: {len(visible)} visible, {len(holdout)} holdout triples")
                r = _evaluate(f_fn, holdout)
                print(f"  score={r['score']}, max_res={r['max_abs_residual']}")
                print("smoke-test: PASSED")
                return 0

            if args.emit_deterministic_gates:
                print(json.dumps(_evaluate(f_fn, holdout)))
                return 0

            if args.run_visible_assertions:
                fails = sum(1 for u, v, z in visible if _safe_call(f_fn, u, v) != z)
                print(f"visible-slice: {fails}/{len(visible)} failures")
                return 0 if fails == 0 else 1

            if args.eval_results_path:
                hr = _evaluate(f_fn, holdout)
                vr = _evaluate(f_fn, visible)
                output = {
                    "generated_on": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "score": hr["score"],
                    "weakest_point": hr["weakest_point"],
                    "score_contract": {
                        "mode": "integer_exact_match",
                        "exact_match_fraction": hr["exact_match_fraction"],
                        "max_abs_residual": hr["max_abs_residual"],
                        "visible_exact_match": vr["exact_match_fraction"],
                        "holdout_hard_gate_passed": hr["harness_ok"],
                    },
                }
                Path(args.eval_results_path).write_text(json.dumps(output, indent=2))
                return 0

            return _evaluate(f_fn, holdout)["score"]


        if __name__ == "__main__":
            sys.exit(main(sys.argv[1:]))
    ''')
    (project_dir / "gate_harness.py").write_text(content, encoding="utf-8")


def _write_test_model(project_dir: Path, variables: list[str]):
    """Write trivial baseline test_model.py (Division B artifact)."""
    var_sig = ", ".join(variables)
    content = f'MODEL_PARAMS = {{"dummy": 0.0}}\n\ndef f({var_sig}):\n    return 0\n'
    (project_dir / "test_model.py").write_text(content, encoding="utf-8")


def _write_thesis(project_dir: Path, problem_brief: str, continuous: bool = False):
    """Write neutral seed thesis (Division B artifact).

    continuous=True: avoids integer/exact-match language.
    """
    if continuous:
        goal_line = (
            "find a closed-form mathematical law f that accurately describes the "
            "data and generalizes to held-out inputs."
        )
    else:
        goal_line = (
            "find a deterministic law — whether closed-form expression, recurrence "
            "relation, or algorithmic rule — that exactly reproduces every observed "
            "value and generalizes beyond the visible range."
        )
    content = textwrap.dedent(f"""\
        # Investigation

        We are investigating {problem_brief}.

        The evidence consists of observed input-output pairs. Our goal is to
        {goal_line}

        No specific law has been proposed yet. The first step is to
        identify the primary structural pattern in the data.
    """)
    (project_dir / "thesis.md").write_text(content, encoding="utf-8")


def _write_charter(
    project_dir: Path,
    problem_brief: str,
    variables: list[str],
    continuous: bool = False,
):
    """Write neutral project charter (Division B artifact).

    continuous=True: removes integer/exact-match language; uses RMSE framing.
    """
    var_str = ", ".join(variables)
    if continuous:
        core_question = (
            f"Find a mathematical formula f({var_str}) — expressed as a Python function — "
            f"that accurately reproduces the observed data in evidence.txt and generalises "
            f"to held-out data. The formula may take any closed-form mathematical structure."
        )
        problem_type = f"{problem_brief.capitalize()}."
        success = [
            f"f({var_str}) fits all visible evidence points with low relative error",
            "The formula generalises to held-out data",
            "The formula is parsimonious and structurally motivated",
        ]
        failure = [
            "Large residuals on visible or holdout data",
            "Lookup tables, piecewise interpolation, or memorisation",
            "Unexplained complexity — more parameters than the structure demands",
        ]
        out_of_scope = [
            "External domain knowledge or named scientific laws",
            "Hard-coded constants taken from reference tables rather than derived from data",
        ]
    else:
        core_question = (
            f"Find a law governing f({var_str}) — expressed as a Python function — that "
            f"exactly reproduces every observed integer value in evidence.txt and "
            f"generalizes to held-out data. The law may take any form: a closed-form "
            f"expression, a recurrence relation, an algorithmic rule, or any other "
            f"deterministic computation."
        )
        problem_type = (
            f"{problem_brief.capitalize()}. The function takes integer inputs and produces "
            f"integer outputs. Exact match on every evidence point is required."
        )
        success = [
            f"f({var_str}) matches all visible evidence points exactly",
            "The law generalizes to held-out data",
            "The law is parsimonious and mechanistically motivated",
        ]
        failure = [
            "Any evidence point has a non-zero residual",
            "The law is a lookup table or interpolation polynomial",
            "The law uses piecewise rules without structural justification",
        ]
        out_of_scope = [
            "Approximate or statistical models",
            "External domain knowledge or named scientific laws",
            "Importing from known sequence databases",
        ]

    success_str = "\n".join(f"        - {s}" for s in success)
    failure_str = "\n".join(f"        - {f}" for f in failure)
    scope_str = "\n".join(f"        - {o}" for o in out_of_scope)

    content = textwrap.dedent(f"""\
        # Project Charter

        ## Core Question
        {core_question}

        ## Problem Description
        {problem_type}

        ## Success States
{success_str}

        ## Failure States
{failure_str}

        ## Out of Scope
{scope_str}
    """)
    (project_dir / "project_charter.md").write_text(content, encoding="utf-8")


def _write_denylist(project_dir: Path, patterns: list[str]):
    """Write GT-specific denylist (Division A artifact)."""
    lines = ["# GT-specific denylist for leak sentinel (auto-generated)"]
    for p in patterns:
        lines.append(p.strip())
    (project_dir / ".denylist").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_rubric(
    rubric_path: Path,
    slug: str,
    problem_brief: str,
    variables: list[str],
    continuous: bool = False,
    rmse_threshold: float = 0.15,
    composition_stagnation_threshold: int = 3,
    gp103_stagnation_threshold: int = 1,
    discovery_mode: bool = False,
):
    """Write scoring rubric (Division B artifact — GT-blind).

    continuous=True: emits continuous_rmse mode, float persona, no integer-exact language.
    discovery_mode=True: disables Component C (GP-075 contamination constraint).
    composition_stagnation_threshold: iterations before Component D fires (default 3).
    gp103_stagnation_threshold: iterations before H-GP103-5 compositor fires (default 1).
    """
    var_str = ", ".join(variables)

    if continuous:
        fit_score_mode = "continuous_rmse"
        enable_cc = False if discovery_mode else True
        persona = (
            f"You are a skeptical mathematician investigating {problem_brief}. "
            f"You demand that any proposed f({var_str}) fit all visible data points "
            f"with low relative residuals and generalise accurately to held-out coordinates. "
            f"Every functional term must be derived step-by-step from the data pattern. "
            f"You are hostile to lookup tables, piecewise interpolation, and formulas "
            f"that name specific scientific laws or constants. "
            f"Parsimony means structural justification, not an absolute parameter count: "
            f"a model with more parameters is preferred when each parameter is structurally "
            f"motivated by a distinct observed data regime. "
            f"You penalise ungrounded parameter bloat, but accept parameters that are "
            f"structurally necessary to capture the data's full dynamic range."
        )
        dim_fit = {
            "name": "Fit Quality on Visible Set",
            "weight": 50,
            "description": (
                f"Does f({var_str}) closely reproduce the observable for every "
                f"data tuple in evidence.txt? Low relative residuals required. "
                f"A model with large residuals has a structural defect. "
                f"Suspiciously near-zero residuals on a complex observable may indicate overfitting."
            ),
        }
        crit_fit = (
            f"Does f({var_str}) return values within {rmse_threshold*100:.0f}% "
            f"relative error for every data tuple in evidence.txt?"
        )
    else:
        fit_score_mode = "discrete_exact"
        enable_cc = True
        persona = (
            f"You are a skeptical mathematician investigating {problem_brief}. "
            f"You demand exact integer match on every evidence point and insist "
            f"that every term in a proposed f({var_str}) be derived step-by-step "
            f"from observed data tuples. You are hostile to lookup tables, "
            f"piecewise hacks, and named-import shortcuts."
        )
        dim_fit = {
            "name": "Exact Match on Visible Set",
            "weight": 50,
            "description": (
                f"Does f({var_str}) produce the exact integer z for every "
                f"data tuple in evidence.txt? A model that misses a single "
                f"point has a structural defect."
            ),
        }
        crit_fit = (
            f"Does f({var_str}) return the exact integer z for every "
            f"data tuple in evidence.txt?"
        )

    rubric: dict = {
        "rubric_version": "1.0",
        "project": slug,
        "falsification_mode": "bounded_discriminator",
        "enable_fit_primitive": True,
        "enable_component_c": enable_cc,
        "fit_score_mode": fit_score_mode,
        "fit_required_dimensionality": len(variables),
        "fit_required_vars": variables,
        "holdout_hard_gate": True,
        "target_convention_homogeneity": "homogeneous",  # GP-162 R9: generated substrates are always single-convention
        "composition_stagnation_threshold": composition_stagnation_threshold,
        "gp103_stagnation_threshold": gp103_stagnation_threshold,
        "persona": persona,
        "dimensions": [
            dim_fit,
            {
                "name": "Structural Derivation",
                "weight": 30,
                "description": (
                    f"Does the thesis derive the functional form step-by-step "
                    f"from specific data tuples? Every term and constant must "
                    f"be motivated by a data observation."
                ),
            },
            {
                "name": "Generalization Quality",
                "weight": 20,
                "description": (
                    f"Is the formula structurally justified and likely to generalize "
                    f"beyond the visible range? A model that maps distinct structural "
                    f"terms to distinct observed data regimes is preferred over one "
                    f"tuned to the visible window. Penalize ungrounded parameter bloat, "
                    f"memorization, and unnecessary complexity."
                ),
            },
        ],
        "criteria": {
            "1_Fit_Quality_Visible": crit_fit,
            "2_Structural_Derivation": (
                f"Does the thesis show at least three explicit intermediate "
                f"steps, each citing specific data tuples?"
            ),
            "3_Generalization_Quality": (
                f"Is the formula structurally justified and free of ungrounded parameter bloat? "
                f"Would it generalize to unseen inputs without overfitting? "
                f"Do not penalize a model for having more parameters if each parameter "
                f"is motivated by a distinct observed data regime."
            ),
        },
    }

    if not enable_cc:
        rubric["discovery_mode"] = True
    else:
        rubric["component_c_gt_module"] = f"src.ztare.substrates.{slug}_gt"

    if continuous and rmse_threshold != 0.15:
        rubric["fit_rmse_threshold"] = rmse_threshold

    # GP-157 Gap #3b (2026-04-25 night): auto-classify substrate from
    # the visible-evidence target column and write cage_meta.class +
    # source provenance into the rubric. Pushes substrate-class
    # determination upstream from operator-tagging (gp159 wrong-class
    # source) to data-driven probes. Per panel: 'humans lie or make
    # mistakes; the data's shape dictates its routing'.
    try:
        from src.ztare.scaffold.substrate_probe import (
            classify_substrate as _classify_substrate,
            SubstrateClass as _SubstrateClass,
        )
        # Extract y-column from visible_triples (already in scope as
        # `triples`/`visible_triples`; signature varies by code path).
        # Fall back gracefully if format unknown.
        _y_column: list[float] = []
        try:
            _y_column = [float(t[-1]) for t in (triples if "triples" in dir() else [])]
        except Exception:
            _y_column = []
        if len(_y_column) >= 5:
            _result = _classify_substrate(_y_column)
            _existing_meta = rubric.get("cage_meta") or {}
            if _result.detected != _SubstrateClass.AMBIGUOUS:
                _existing_meta.setdefault("class", _result.detected.value)
                _existing_meta.setdefault("class_provenance", "auto_classified_at_ingestion")
            else:
                # NO SILENT DEFAULT (panel Failure Mode 2 + Epistemic Handshake).
                # When probes can't decide, refuse to guess — write a sentinel
                # value that make seal will reject, forcing operator declaration
                # OR an explicit LLM-handshake run before any iter spend.
                _existing_meta.setdefault("class", "_ambiguous_pending_review")
                _existing_meta.setdefault("class_provenance", "auto_classification_inconclusive")
            _existing_meta.setdefault("class_confidence", _result.confidence)
            _existing_meta.setdefault("class_diagnostics", _result.diagnostics)
            rubric["cage_meta"] = _existing_meta
    except Exception:
        # Auto-classification is best-effort — if the probe module is
        # unavailable or the data shape is unfamiliar, leave cage_meta
        # for manual operator declaration.
        pass

    rubric_path.write_text(json.dumps(rubric, indent=2) + "\n", encoding="utf-8")


def generate_substrate(
    slug: str,
    gt_expr: str | None,
    dominant_expr: str | None,
    variables: list[str],
    visible_ranges: dict[str, tuple[float, float]],
    holdout_ranges: dict[str, tuple[float, float]],
    problem_brief: str,
    denylist_patterns: list[str],
    transform: str | None = None,
    transform_scale: int = 1000,
    gt_script: str | None = None,
    composition_stagnation_threshold: int = 3,
    gp103_stagnation_threshold: int = 1,
    discovery_mode: bool = False,
) -> dict:
    """Generate all substrate artifacts following GP-072 Division A/B protocol.

    New params (2026-04-19):
      composition_stagnation_threshold: iters before Component D fires (rubric field).
      gp103_stagnation_threshold: iters before H-GP103-5 compositor fires (rubric field).
      discovery_mode: sets enable_component_c=False per GP-075 constraint.

    Continuous substrates (GT script exposes evidence_grid() + holdout_grid()):
      - evidence_farther_tail.txt generated from farther_tail_grid() if present.
      - gate_harness emits normalised RMSE (not exact-match).
      - charter/thesis/rubric use float framing.
    """
    project_dir = PROJECTS_DIR / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "workspace").mkdir(exist_ok=True)

    gt_mod = None
    if gt_script:
        gt_fn, gt_mod = _load_gt_script(gt_script, variables)
    else:
        if gt_expr is None:
            raise ValueError("either --gt-expr or --gt-script is required")
        gt_fn = _build_gt_function(gt_expr, variables)

    # Continuous mode: GT script exposes evidence_grid() / holdout_grid() / farther_tail_grid()
    continuous = gt_mod is not None and hasattr(gt_mod, "evidence_grid")
    if continuous:
        visible_triples = _generate_triples_from_grid(gt_fn, gt_mod.evidence_grid(), variables)
        holdout_grid_fn = getattr(gt_mod, "holdout_grid", None)
        if holdout_grid_fn is None:
            raise AttributeError("Continuous GT script must export holdout_grid() alongside evidence_grid()")
        holdout_triples = _generate_triples_from_grid(gt_fn, holdout_grid_fn(), variables)
        # Farther-tail grid is optional for continuous substrates
        tail_grid_fn = getattr(gt_mod, "farther_tail_grid", None)
        tail_triples = (
            _generate_triples_from_grid(gt_fn, tail_grid_fn(), variables)
            if tail_grid_fn is not None else []
        )
    else:
        visible_triples = _generate_triples(
            gt_fn, visible_ranges, variables,
            transform=transform, transform_scale=transform_scale,
        )
        holdout_triples = _generate_triples(
            gt_fn, holdout_ranges, variables,
            transform=transform, transform_scale=transform_scale,
        )
        tail_triples = []  # discrete substrates don't auto-generate farther tail

    _write_evidence(
        project_dir / "evidence.txt", visible_triples, variables,
        f"visible set — {problem_brief}",
    )
    _write_evidence(
        project_dir / "evidence_holdout.txt", holdout_triples, variables,
        "holdout set — NOT visible to mutator",
    )
    if tail_triples:
        _write_evidence(
            project_dir / "evidence_farther_tail.txt", tail_triples, variables,
            "farther-tail set — Division A only; used for farther-tail gate",
        )
    _write_denylist(project_dir, denylist_patterns)

    SUBSTRATES_DIR.mkdir(parents=True, exist_ok=True)
    init_path = SUBSTRATES_DIR / "__init__.py"
    if not init_path.exists():
        init_path.write_text("", encoding="utf-8")
    if not gt_script:
        _write_gt_module(
            SUBSTRATES_DIR / f"{slug}_gt.py",
            gt_expr or "",
            dominant_expr or gt_expr or "",
            variables,
            continuous=continuous,
        )
    else:
        _write_gt_stub(SUBSTRATES_DIR / f"{slug}_gt.py", gt_script)

    # Division B artifacts (GT-blind) — continuous flag propagates through all writers
    _write_gate_harness(project_dir, variables=variables, continuous=continuous)
    _write_test_model(project_dir, variables)
    _write_thesis(project_dir, problem_brief, continuous=continuous)
    _write_charter(project_dir, problem_brief, variables, continuous=continuous)

    rubric_path = RUBRICS_DIR / f"{slug}.json"
    _write_rubric(
        rubric_path, slug, problem_brief, variables,
        continuous=continuous,
        composition_stagnation_threshold=composition_stagnation_threshold,
        gp103_stagnation_threshold=gp103_stagnation_threshold,
        discovery_mode=discovery_mode,
    )

    return {
        "project_dir": str(project_dir),
        "rubric_path": str(rubric_path),
        "gt_module": f"src.ztare.substrates.{slug}_gt",
        "visible_triples": len(visible_triples),
        "holdout_triples": len(holdout_triples),
        "artifacts": [
            str(project_dir / "evidence.txt"),
            str(project_dir / "evidence_holdout.txt"),
            str(project_dir / "gate_harness.py"),
            str(project_dir / "test_model.py"),
            str(project_dir / "thesis.md"),
            str(project_dir / "project_charter.md"),
            str(project_dir / ".denylist"),
            str(rubric_path),
            str(SUBSTRATES_DIR / f"{slug}_gt.py"),
        ],
    }


def main():
    parser = argparse.ArgumentParser(
        description="GP-072 automated substrate generator",
    )
    parser.add_argument("--slug", required=True, help="Project slug (opaque, no GT hints)")
    parser.add_argument("--gt-expr", default=None, help="Ground truth expression (Python syntax)")
    parser.add_argument("--gt-script", default=None, help="Path to GT Python script exporting f_true()")
    parser.add_argument("--dominant-expr", default=None, help="Dominant term expression")
    parser.add_argument("--variables", required=True, help="Comma-separated variable names")
    parser.add_argument("--visible-ranges", required=True, help="Visible ranges: var:lo:hi,...")
    parser.add_argument("--holdout-ranges", required=True, help="Holdout ranges: var:lo:hi,...")
    parser.add_argument("--problem-brief", required=True, help="Neutral problem description (no GT)")
    parser.add_argument("--denylist", default="", help="Comma-separated denylist patterns")
    parser.add_argument("--transform", default=None, choices=["log", "log10"],
                        help="GP-077: transform z-values (e.g. 'log' for exponential sequences)")
    parser.add_argument("--transform-scale", type=int, default=1000,
                        help="Scale factor for transform (default: 1000)")
    parser.add_argument("--run-sentinel", action="store_true", help="Run leak sentinel after generation")
    args = parser.parse_args()

    if not args.gt_expr and not args.gt_script:
        parser.error("either --gt-expr or --gt-script is required")
    if args.gt_expr and args.gt_script:
        parser.error("--gt-expr and --gt-script are mutually exclusive")

    variables = [v.strip() for v in args.variables.split(",")]
    visible_ranges = _parse_ranges(args.visible_ranges)
    holdout_ranges = _parse_ranges(args.holdout_ranges)
    denylist = [p.strip() for p in args.denylist.split(",") if p.strip()]

    result = generate_substrate(
        slug=args.slug,
        gt_expr=args.gt_expr or "0",
        dominant_expr=args.dominant_expr or "0",
        variables=variables,
        visible_ranges=visible_ranges,
        holdout_ranges=holdout_ranges,
        problem_brief=args.problem_brief,
        denylist_patterns=denylist,
        transform=args.transform,
        transform_scale=args.transform_scale,
        gt_script=args.gt_script,
    )

    print(f"\n{'='*60}")
    print(f"SUBSTRATE GENERATED: {args.slug}")
    print(f"{'='*60}")
    print(f"  Project:  {result['project_dir']}")
    print(f"  Rubric:   {result['rubric_path']}")
    print(f"  GT mod:   {result['gt_module']}")
    print(f"  Visible:  {result['visible_triples']} triples")
    print(f"  Holdout:  {result['holdout_triples']} triples")
    print(f"\nArtifacts:")
    for a in result["artifacts"]:
        print(f"  {a}")

    if args.run_sentinel:
        print(f"\n{'='*60}")
        print("RUNNING LEAK SENTINEL")
        print(f"{'='*60}")
        from src.ztare.validator.leak_sentinel import run_sentinel
        hits = run_sentinel(
            Path(result["project_dir"]),
            Path(result["rubric_path"]),
            denylist,
        )
        if not hits:
            print(f"SENTINEL PASSED — {len(denylist)} patterns, 0 matches")
        else:
            total = sum(len(v) for v in hits.values())
            print(f"SENTINEL FAILED — {total} match(es):")
            for fp, file_hits in hits.items():
                for lineno, pat, line_text in file_hits:
                    print(f"  {fp}:{lineno}  pattern={pat!r}")
                    print(f"    {line_text[:120]}")
            sys.exit(1)


if __name__ == "__main__":
    main()
