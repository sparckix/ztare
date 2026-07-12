from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any


_SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "range": range,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}

_FORBIDDEN_NODES = (
    ast.AsyncFor,
    ast.AsyncFunctionDef,
    ast.AsyncWith,
    ast.Attribute,
    ast.Await,
    ast.ClassDef,
    ast.Delete,
    ast.Global,
    ast.Import,
    ast.ImportFrom,
    ast.Lambda,
    ast.Nonlocal,
    ast.Try,
    ast.With,
    ast.Yield,
    ast.YieldFrom,
)

_FORBIDDEN_CALLS = {"__import__", "compile", "eval", "exec", "getattr", "globals", "locals", "open"}

DEFAULT_VISIBLE_JSON_PROBE = """
RESULT = {}
for ref in ARTIFACTS:
    obj = ARTIFACTS[ref]
    summary = {"ref": ref}
    if isinstance(obj, dict):
        summary["container"] = "dict"
        summary["keys"] = sorted(list(obj))[:32]
        for key in ("schema", "relation", "weakness_class", "recommended_capability_id", "recommended_route"):
            if key in obj:
                summary[key] = obj[key]
        for key in ("candidate_top_quotient", "best_prior_top_quotient"):
            if key in obj:
                summary[key] = obj[key]
        if "counterexample_trace" in obj and isinstance(obj["counterexample_trace"], dict):
            trace = obj["counterexample_trace"]
            trace_summary = {}
            for tkey in (
                "schema",
                "exact_rows",
                "wrong_cell_count",
                "failed_gates",
                "first_mismatch",
                "first_mismatch_signature",
                "coordinate_contract",
            ):
                if tkey in trace:
                    trace_summary[tkey] = trace[tkey]
            if "mismatch_classes" in trace and isinstance(trace["mismatch_classes"], list):
                trace_summary["mismatch_classes"] = trace["mismatch_classes"][:4]
            summary["counterexample_trace"] = trace_summary
        for key in ("candidate_regression_receipt", "quotient_comparison"):
            if key in obj and isinstance(obj[key], dict):
                nested = obj[key]
                nested_summary = {"keys": sorted(list(nested))[:32]}
                for nkey in (
                    "schema",
                    "candidate_relation",
                    "relation",
                    "best_prior_exact_rows",
                    "candidate_exact_rows",
                    "best_prior_wrong_cells",
                    "candidate_wrong_cells",
                    "exact_rows_delta",
                    "wrong_cells_delta",
                    "holdout_depth_delta",
                    "first_mismatch",
                ):
                    if nkey in nested:
                        nested_summary[nkey] = nested[nkey]
                if "quotient_comparison" in nested and isinstance(nested["quotient_comparison"], dict):
                    qc = nested["quotient_comparison"]
                    nested_summary["quotient_comparison"] = {
                        qkey: qc[qkey]
                        for qkey in (
                            "relation",
                            "candidate_top_quotient",
                            "best_prior_top_quotient",
                        )
                        if qkey in qc
                    }
                for nkey in ("candidate_top_quotient", "best_prior_top_quotient"):
                    if nkey in nested:
                        nested_summary[nkey] = nested[nkey]
                summary[key] = nested_summary
    elif isinstance(obj, list):
        summary["container"] = "list"
        summary["len"] = len(obj)
        summary["head"] = obj[:3]
    else:
        summary["container"] = "scalar"
        summary["value"] = obj
    RESULT[ref] = summary
""".strip()


def run_visible_json_probe(
    *,
    project_dir: str | Path,
    artifact_refs: list[str],
    probe_py: str,
    max_output_chars: int = 3000,
) -> dict[str, Any]:
    """Run a bounded Python probe over visible JSON artifacts.

    The probe is an in-process pure transform, not terminal access. It receives
    `ARTIFACTS`, may use a small builtin set, and must assign `RESULT` to a
    JSON-serializable value. Artifact refs are project-relative and may not
    escape the project tree.
    """
    project = Path(project_dir).resolve()
    code = str(probe_py or "").strip()
    if not code:
        code = DEFAULT_VISIBLE_JSON_PROBE
    refs = [str(ref).strip() for ref in artifact_refs if str(ref).strip()]
    if not refs:
        raise ValueError("run_visible_json_probe requires non-empty `artifact_refs`.")
    tree = ast.parse(code, mode="exec")
    _validate_probe_ast(tree)
    artifacts: dict[str, Any] = {}
    artifact_hashes: dict[str, str] = {}
    for ref in refs:
        path = (project / ref).resolve()
        try:
            path.relative_to(project)
        except ValueError as exc:
            raise ValueError(f"artifact_ref escapes project: {ref}") from exc
        if not path.exists() or not path.is_file():
            raise ValueError(f"artifact_ref does not exist: {ref}")
        raw = path.read_bytes()
        artifact_hashes[ref] = hashlib.sha256(raw).hexdigest()
        artifacts[ref] = json.loads(raw.decode("utf-8"))
    namespace: dict[str, Any] = {"ARTIFACTS": artifacts, "RESULT": None}
    exec(compile(tree, "<leaf-visible-json-probe>", "exec"), {"__builtins__": _SAFE_BUILTINS}, namespace)
    result = namespace.get("RESULT")
    try:
        result_json = json.dumps(result, sort_keys=True, separators=(",", ":"), default=str)
    except TypeError as exc:
        raise ValueError("run_visible_json_probe RESULT must be JSON-serializable.") from exc
    if len(result_json) > max_output_chars:
        result_summary = result_json[: max_output_chars - 20] + "...<truncated>"
    else:
        result_summary = result_json
    return {
        "schema": "ztare-visible-json-probe-result-v1",
        "probe_sha256": hashlib.sha256(code.encode("utf-8")).hexdigest(),
        "artifact_hashes": artifact_hashes,
        "result": result,
        "result_summary": result_summary,
    }


def _validate_probe_ast(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if isinstance(node, _FORBIDDEN_NODES):
            raise ValueError(f"run_visible_json_probe forbids AST node {type(node).__name__}.")
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise ValueError("run_visible_json_probe forbids dunder names.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in _FORBIDDEN_CALLS:
                raise ValueError(f"run_visible_json_probe forbids call {node.func.id}().")
