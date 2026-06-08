#!/usr/bin/env python3
"""Apply event-family caps to Polymarket Law 3 candidates.

No DB mutation and no model calls. This answers whether the acquired Polymarket
candidate set still fills the target cells after dependence control.
"""
from __future__ import annotations

import argparse
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_MANIFEST = WORKSPACE / "cutoff_polymarket_pre_cutoff_candidate_manifest.jsonl"
DEFAULT_TARGETS = WORKSPACE / "cutoff_second_source_pre_cutoff_acquisition_targets.jsonl"
DEFAULT_OUT = WORKSPACE


def repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def target_counts(path: Path) -> dict[tuple[str, str, str], int]:
    out: dict[tuple[str, str, str], int] = {}
    for row in read_jsonl(path):
        if row.get("source") != "polymarket":
            continue
        key = (
            str(row.get("source")),
            str(row.get("freeze_value_band")),
            str(row.get("question_length_band")),
        )
        out[key] = out.get(key, 0) + int(row.get("target_pre_cutoff_rows") or 0)
    return out


def cell_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("source")),
        str(row.get("freeze_value_band")),
        str(row.get("question_length_band")),
    )


def event_key(row: dict[str, Any]) -> str:
    return str(row.get("event_slug") or row.get("slug") or row.get("contract_id"))


def volume(row: dict[str, Any]) -> float:
    try:
        return float(row.get("volume_num") or 0.0)
    except Exception:
        return 0.0


def option_sets(rows: list[dict[str, Any]], max_per_event_family: int) -> list[list[dict[str, Any]]]:
    if max_per_event_family < 1:
        raise ValueError("max_per_event_family must be >= 1")
    by_event: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_event[event_key(row)].append(row)
    options: list[list[dict[str, Any]]] = []
    for event_rows in by_event.values():
        event_rows = sorted(event_rows, key=volume, reverse=True)
        choices: list[list[dict[str, Any]]] = [[]]
        for k in range(1, min(max_per_event_family, len(event_rows)) + 1):
            choices.extend(list(combo) for combo in itertools.combinations(event_rows, k))
        options.append(choices)
    return options


def capped_selection(
    rows: list[dict[str, Any]],
    targets: dict[tuple[str, str, str], int],
    *,
    max_per_event_family: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    keys = sorted(targets)
    caps = tuple(targets[key] for key in keys)
    index = {key: i for i, key in enumerate(keys)}
    states: dict[tuple[int, ...], tuple[float, list[dict[str, Any]]]] = {
        tuple(0 for _ in keys): (0.0, [])
    }
    for choices in option_sets(rows, max_per_event_family):
        next_states = dict(states)
        for state, (vol_score, selected) in states.items():
            for choice in choices:
                if not choice:
                    continue
                new_state = list(state)
                add_rows: list[dict[str, Any]] = []
                add_vol = 0.0
                for row in choice:
                    key = cell_key(row)
                    if key not in index:
                        continue
                    i = index[key]
                    if new_state[i] >= caps[i]:
                        continue
                    new_state[i] += 1
                    add_rows.append(row)
                    add_vol += volume(row)
                if not add_rows:
                    continue
                new_state_t = tuple(new_state)
                candidate_score = vol_score + add_vol
                old = next_states.get(new_state_t)
                if old is None or candidate_score > old[0]:
                    next_states[new_state_t] = (candidate_score, selected + add_rows)
        states = next_states
    best_state, (best_vol, best_rows) = max(
        states.items(),
        key=lambda item: (sum(item[0]), item[1][0]),
    )
    metadata = {
        "target_keys": [" | ".join(key) for key in keys],
        "target_counts": {" | ".join(key): targets[key] for key in keys},
        "selected_state": {" | ".join(key): best_state[i] for i, key in enumerate(keys)},
        "selected_volume_score": best_vol,
    }
    return best_rows, metadata


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    rows = read_jsonl(args.manifest)
    targets = target_counts(args.targets)
    selected, meta = capped_selection(rows, targets, max_per_event_family=args.max_per_event_family)
    selected_ids = {str(row.get("contract_id")) for row in selected}
    dropped = [row for row in rows if str(row.get("contract_id")) not in selected_ids]
    selected_by_cell = Counter(" | ".join(cell_key(row)) for row in selected)
    dropped_by_cell = Counter(" | ".join(cell_key(row)) for row in dropped)
    event_counts = Counter(event_key(row) for row in selected)
    deficits = []
    for key, need in sorted(targets.items()):
        key_text = " | ".join(key)
        got = selected_by_cell.get(key_text, 0)
        if got < need:
            deficits.append(
                {
                    "source": key[0],
                    "freeze_value_band": key[1],
                    "question_length_band": key[2],
                    "target_pre_cutoff_rows": need,
                    "selected_rows": got,
                    "deficit": need - got,
                }
            )
    return {
        "schema": "gp245-polymarket-event-family-cap-v1",
        "manifest": repo_rel(args.manifest),
        "targets": repo_rel(args.targets),
        "max_per_event_family": args.max_per_event_family,
        "input_rows": len(rows),
        "selected_rows": len(selected),
        "dropped_rows": len(dropped),
        "target_rows": sum(targets.values()),
        "selected_unique_event_families": len(event_counts),
        "selected_by_cell": dict(sorted(selected_by_cell.items())),
        "dropped_by_cell": dict(sorted(dropped_by_cell.items())),
        "deficits": deficits,
        "selected_event_family_counts": dict(event_counts.most_common()),
        "target_metadata": meta,
        "selected_manifest": selected,
        "dropped_manifest": dropped,
        "interpretation": (
            "This dependence-control preview caps selected rows per event family. "
            "It does not resolve manual provenance flags; it only quantifies how "
            "much target coverage survives event-family capping."
        ),
    }


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# Polymarket Event-Family Cap Preview",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Max per event family: {report['max_per_event_family']}",
        f"- Input rows: {report['input_rows']}",
        f"- Target rows: {report['target_rows']}",
        f"- Selected rows: {report['selected_rows']}",
        f"- Dropped rows: {report['dropped_rows']}",
        f"- Selected unique event families: {report['selected_unique_event_families']}",
        "",
        "## Selected By Cell",
        "",
        "```json",
        json.dumps(report["selected_by_cell"], indent=2, sort_keys=True),
        "```",
        "",
        "## Deficits",
        "",
        "```json",
        json.dumps(report["deficits"], indent=2, sort_keys=True),
        "```",
        "",
        "## Dropped By Cell",
        "",
        "```json",
        json.dumps(report["dropped_by_cell"], indent=2, sort_keys=True),
        "```",
        "",
        "## Selected Event Families",
        "",
        "```json",
        json.dumps(report["selected_event_family_counts"], indent=2, sort_keys=True),
        "```",
        "",
        "## Interpretation",
        "",
        report["interpretation"],
        "",
    ]
    return "\n".join(lines)


def write_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cutoff_polymarket_event_family_cap_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "cutoff_polymarket_event_family_cap_report.md").write_text(
        render_md(report),
        encoding="utf-8",
    )
    with (out_dir / "cutoff_polymarket_event_family_cap_selected.jsonl").open("w", encoding="utf-8") as f:
        for row in report["selected_manifest"]:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    with (out_dir / "cutoff_polymarket_event_family_cap_dropped.jsonl").open("w", encoding="utf-8") as f:
        for row in report["dropped_manifest"]:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--targets", type=Path, default=DEFAULT_TARGETS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--max-per-event-family", type=int, default=1)
    args = parser.parse_args()
    report = build_report(args)
    write_outputs(report, args.out_dir)
    print(json.dumps({k: report[k] for k in (
        "input_rows",
        "target_rows",
        "selected_rows",
        "dropped_rows",
        "selected_by_cell",
        "deficits",
    )}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
