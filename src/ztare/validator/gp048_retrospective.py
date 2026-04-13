"""GP-048 retrospective analyzer.

One-off read-only tool: given a project workspace containing
`fit_result_iter_*.json` files, compute per-iter primitive sets and a
pairwise tree-edit-distance matrix over the champion expressions.

This is the Candidate E move from the ztare_discovery_vs_benchmarking seam:
analyze the data we already have before running another experiment.

Usage:
    python -m src.ztare.validator.gp048_retrospective <workspace_dir> [--focus iter1,iter2,...]

Output:
    <workspace_dir>/gp048_retrospective.json  (structured)
    <workspace_dir>/gp048_retrospective.md    (human-readable)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from src.ztare.validator.structural_memory import (
    ExpressionParseError,
    extract_primitives,
    normalize_expression,
    tree_edit_distance,
)


FIT_RESULT_PATTERN = re.compile(r"fit_result_iter_(\d+)\.json$")


@dataclass
class IterationRecord:
    iteration: int
    expression: str
    independent_vars: list[str]
    parameter_names: list[str]
    max_abs_residual: float
    rmse: float
    primitives: set[str]
    tree: object  # normalized AST


def _load_fit_results(workspace: Path) -> list[IterationRecord]:
    records: list[IterationRecord] = []
    for path in sorted(workspace.glob("fit_result_iter_*.json")):
        match = FIT_RESULT_PATTERN.search(path.name)
        if not match:
            continue
        iteration = int(match.group(1))
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"WARN: failed to read {path.name}: {exc}", file=sys.stderr)
            continue
        if data.get("status") != "success":
            continue
        expression = data.get("expression")
        if not isinstance(expression, str):
            continue
        independent_vars = list(data.get("independent_vars", []))
        parameter_names = list(data.get("parameter_names", []))
        try:
            tree = normalize_expression(expression, independent_vars, parameter_names)
        except ExpressionParseError as exc:
            print(f"WARN: parse error iter {iteration}: {exc}", file=sys.stderr)
            continue
        primitives = extract_primitives(tree)
        records.append(
            IterationRecord(
                iteration=iteration,
                expression=expression,
                independent_vars=independent_vars,
                parameter_names=parameter_names,
                max_abs_residual=float(data.get("max_abs_residual", float("nan"))),
                rmse=float(data.get("rmse", float("nan"))),
                primitives=primitives,
                tree=tree,
            )
        )
    return records


def _pairwise_ted(records: list[IterationRecord]) -> dict[tuple[int, int], int]:
    matrix: dict[tuple[int, int], int] = {}
    for i, a in enumerate(records):
        for b in records[i:]:
            d = tree_edit_distance(a.tree, b.tree)
            matrix[(a.iteration, b.iteration)] = d
            matrix[(b.iteration, a.iteration)] = d
    return matrix


def _find_clusters(records: list[IterationRecord], matrix: dict[tuple[int, int], int], threshold: int) -> list[list[int]]:
    """Union-find clustering: iters with TED <= threshold belong to same cluster."""
    parent: dict[int, int] = {r.iteration: r.iteration for r in records}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for (a, b), d in matrix.items():
        if a < b and d <= threshold:
            union(a, b)

    clusters: dict[int, list[int]] = {}
    for it in parent:
        root = find(it)
        clusters.setdefault(root, []).append(it)
    return sorted((sorted(c) for c in clusters.values()), key=lambda c: (-len(c), c[0]))


def analyze(workspace: Path, focus: list[int] | None = None, cluster_threshold: int = 3) -> dict:
    records = _load_fit_results(workspace)
    matrix = _pairwise_ted(records)
    clusters = _find_clusters(records, matrix, threshold=cluster_threshold)

    focus_records = None
    focus_matrix = None
    if focus:
        focus_set = set(focus)
        focus_records = [r for r in records if r.iteration in focus_set]
        focus_matrix = [[matrix[(a.iteration, b.iteration)] for b in focus_records] for a in focus_records]

    return {
        "workspace": str(workspace),
        "records": [
            {
                "iteration": r.iteration,
                "expression": r.expression,
                "independent_vars": r.independent_vars,
                "parameter_names": r.parameter_names,
                "max_abs_residual": r.max_abs_residual,
                "rmse": r.rmse,
                "primitives": sorted(r.primitives),
            }
            for r in records
        ],
        "pairwise_ted": [
            {"a": a, "b": b, "ted": d}
            for (a, b), d in sorted(matrix.items())
            if a <= b
        ],
        "clusters": [
            {"size": len(c), "iterations": c} for c in clusters
        ],
        "focus": {
            "iterations": focus or [],
            "ted_matrix": focus_matrix,
            "expressions": [r.expression for r in focus_records] if focus_records else [],
            "primitive_sets": [sorted(r.primitives) for r in focus_records] if focus_records else [],
        } if focus else None,
        "cluster_threshold": cluster_threshold,
    }


def _render_markdown(report: dict) -> str:
    lines: list[str] = []
    lines.append("# GP-048 Retrospective Report")
    lines.append("")
    lines.append(f"**Workspace:** `{report['workspace']}`")
    lines.append(f"**Cluster threshold (TED):** ≤ {report['cluster_threshold']}")
    lines.append(f"**Iterations analyzed:** {len(report['records'])}")
    lines.append("")

    lines.append("## Per-iteration primitive sets")
    lines.append("")
    lines.append("| Iter | max_abs_residual | primitives |")
    lines.append("|---:|---:|---|")
    for r in report["records"]:
        prims = ", ".join(r["primitives"])
        lines.append(f"| {r['iteration']} | {r['max_abs_residual']:.4g} | {prims} |")
    lines.append("")

    lines.append("## Clusters (TED-connected components)")
    lines.append("")
    for i, c in enumerate(report["clusters"], 1):
        lines.append(f"- **Cluster {i}** (size {c['size']}): iters {c['iterations']}")
    lines.append("")

    focus = report.get("focus")
    if focus:
        lines.append(f"## Focus subset: iters {focus['iterations']}")
        lines.append("")
        if focus["ted_matrix"]:
            header = "| | " + " | ".join(str(i) for i in focus["iterations"]) + " |"
            sep = "|---|" + "|".join(["---:"] * len(focus["iterations"])) + "|"
            lines.append(header)
            lines.append(sep)
            for i, row in zip(focus["iterations"], focus["ted_matrix"]):
                lines.append("| " + str(i) + " | " + " | ".join(str(v) for v in row) + " |")
            lines.append("")
        lines.append("### Expressions")
        for it, expr in zip(focus["iterations"], focus["expressions"]):
            lines.append(f"- **iter {it}:** `{expr}`")
        lines.append("")
        lines.append("### Primitive sets")
        for it, prims in zip(focus["iterations"], focus["primitive_sets"]):
            lines.append(f"- **iter {it}:** {', '.join(prims)}")
        lines.append("")

    lines.append("## Pairwise TED (all iters, ai<bj)")
    lines.append("")
    lines.append("| a | b | TED |")
    lines.append("|---:|---:|---:|")
    for entry in report["pairwise_ted"]:
        if entry["a"] == entry["b"]:
            continue
        lines.append(f"| {entry['a']} | {entry['b']} | {entry['ted']} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GP-048 retrospective AST analyzer")
    parser.add_argument("workspace", type=Path, help="Project workspace dir with fit_result_iter_*.json")
    parser.add_argument("--focus", type=str, default="", help="Comma-separated iter numbers to spotlight")
    parser.add_argument("--cluster-threshold", type=int, default=3, help="TED threshold for cluster grouping")
    parser.add_argument("--out", type=Path, default=None, help="Output json path (default: workspace/gp048_retrospective.json)")
    args = parser.parse_args(argv)

    workspace = args.workspace.resolve()
    if not workspace.is_dir():
        print(f"ERROR: not a directory: {workspace}", file=sys.stderr)
        return 2

    focus = [int(x) for x in args.focus.split(",") if x.strip()] if args.focus else None

    report = analyze(workspace, focus=focus, cluster_threshold=args.cluster_threshold)

    out_json = args.out or (workspace / "gp048_retrospective.json")
    out_md = out_json.with_suffix(".md")
    out_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(_render_markdown(report), encoding="utf-8")

    print(f"wrote {out_json}")
    print(f"wrote {out_md}")
    print(f"iterations analyzed: {len(report['records'])}")
    print(f"clusters (threshold {args.cluster_threshold}): {len(report['clusters'])}")
    for i, c in enumerate(report["clusters"], 1):
        print(f"  cluster {i}: size {c['size']} iters {c['iterations']}")
    if focus:
        print(f"focus subset {focus}:")
        for it, prims in zip(report["focus"]["iterations"], report["focus"]["primitive_sets"]):
            print(f"  iter {it}: {prims}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
