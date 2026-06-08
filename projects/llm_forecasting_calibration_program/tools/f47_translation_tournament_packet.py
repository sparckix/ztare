#!/usr/bin/env python3
"""Build an overlapping F47 tournament packet for ranking-to-probability tests.

The first source-balanced F47 consumer packet proved pairwise ranking, but each
contract appeared in exactly one pair. That graph cannot identify per-contract
latent scores for Bradley-Terry, Thurstone, Elo, or held-out Brier translation.

This packet reuses the same resolved contracts and builds a source-wise
opposite-outcome tournament graph. Within each source, each YES contract is
paired with two NO contracts in a ring, giving every contract degree two when
YES/NO counts are balanced. Outcomes are written only to the answer key.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
WORKSPACE = (
    REPO
    / "projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace"
)
DEFAULT_BASE_QUEUE = WORKSPACE / "f47_source_balanced_consumer_packet_2026_06_03_dispatch_queue.jsonl"
DEFAULT_BASE_KEY = WORKSPACE / "f47_source_balanced_consumer_packet_2026_06_03_answer_key.json"
DEFAULT_QUEUE = WORKSPACE / "f47_translation_tournament_packet_2026_06_03_dispatch_queue.jsonl"
DEFAULT_KEY = WORKSPACE / "f47_translation_tournament_packet_2026_06_03_answer_key.json"
DEFAULT_REPORT = WORKSPACE / "f47_translation_tournament_packet_2026_06_03_report.md"

REQUIRED_OUTPUT_FIELDS = [
    "p_success_a",
    "p_success_b",
    "predicted_delta",
    "delta_driver",
    "rationale_short",
]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_base_contracts(
    queue_path: Path, key_path: Path
) -> dict[str, dict[str, dict[str, Any]]]:
    """Return source -> contract_id -> contract record with hidden y."""
    key_data = json.loads(key_path.read_text())["answer_key"]
    y_by_contract: dict[str, int] = {}
    source_by_contract: dict[str, str] = {}
    for row in key_data:
        source = str(row["source"])
        y_by_contract[str(row["contract_id_a"])] = int(row["y_a"])
        y_by_contract[str(row["contract_id_b"])] = int(row["y_b"])
        source_by_contract[str(row["contract_id_a"])] = source
        source_by_contract[str(row["contract_id_b"])] = source

    contracts_by_source: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in read_jsonl(queue_path):
        source = str(row["source"])
        for side in ("contract_a", "contract_b"):
            contract = dict(row[side])
            contract_id = str(contract["contract_id"])
            if contract_id not in y_by_contract:
                raise SystemExit(f"missing outcome for {contract_id}")
            if source_by_contract[contract_id] != source:
                raise SystemExit(f"source mismatch for {contract_id}")
            contract["source"] = source
            contract["y_known"] = y_by_contract[contract_id]
            contracts_by_source[source][contract_id] = contract
    return contracts_by_source


def length_bucket(question: str) -> str:
    n = len(question)
    if n < 90:
        return "short"
    if n < 220:
        return "medium"
    return "long"


def connected_components(nodes: set[str], edges: list[tuple[str, str]]) -> list[set[str]]:
    remaining = set(nodes)
    adjacency: dict[str, set[str]] = {node: set() for node in nodes}
    for a, b in edges:
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)
    comps: list[set[str]] = []
    while remaining:
        start = remaining.pop()
        comp = {start}
        q: deque[str] = deque([start])
        while q:
            node = q.popleft()
            for nxt in adjacency.get(node, set()):
                if nxt in remaining:
                    remaining.remove(nxt)
                    comp.add(nxt)
                    q.append(nxt)
        comps.append(comp)
    return comps


def build_source_edges(source: str, contracts: dict[str, dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    yes = sorted(
        [c for c in contracts.values() if int(c["y_known"]) == 1],
        key=lambda c: (len(str(c.get("question") or "")), str(c["contract_id"])),
    )
    no = sorted(
        [c for c in contracts.values() if int(c["y_known"]) == 0],
        key=lambda c: (len(str(c.get("question") or "")), str(c["contract_id"])),
    )
    if not yes or not no:
        raise SystemExit(f"{source} needs both YES and NO contracts")
    # Ring design: each YES connects to two neighboring NOs. This gives a
    # connected bipartite graph for balanced sources and still works when
    # counts differ, though degrees may not be equal.
    edges: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for i, yes_contract in enumerate(yes):
        candidates = [no[i % len(no)], no[(i - 1) % len(no)]]
        seen: set[str] = set()
        for no_contract in candidates:
            no_id = str(no_contract["contract_id"])
            if no_id in seen:
                continue
            seen.add(no_id)
            edges.append((yes_contract, no_contract))
    return edges


def build_packet(
    queue_path: Path, key_path: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    contracts_by_source = load_base_contracts(queue_path, key_path)
    dispatch: list[dict[str, Any]] = []
    answer_key: list[dict[str, Any]] = []
    source_reports: dict[str, Any] = {}
    global_i = 0

    for source in sorted(contracts_by_source):
        contracts = contracts_by_source[source]
        edges = build_source_edges(source, contracts)
        degree: Counter[str] = Counter()
        graph_edges: list[tuple[str, str]] = []
        for local_i, (yes_contract, no_contract) in enumerate(edges):
            global_i += 1
            # Alternate A-position independently of outcome.
            if local_i % 2 == 0:
                a, b = yes_contract, no_contract
            else:
                a, b = no_contract, yes_contract
            a_id = str(a["contract_id"])
            b_id = str(b["contract_id"])
            degree[a_id] += 1
            degree[b_id] += 1
            graph_edges.append((a_id, b_id))
            pair_id = f"f47_translate_{global_i:03d}_{source}"
            dispatch.append(
                {
                    "pair_id": pair_id,
                    "source": source,
                    "question_length_bucket_a": length_bucket(str(a.get("question") or "")),
                    "question_length_bucket_b": length_bucket(str(b.get("question") or "")),
                    "contract_a": {
                        "contract_id": a_id,
                        "question": a.get("question") or "",
                        "task_type": a.get("task_type") or "",
                        "horizon": a.get("horizon") or "",
                    },
                    "contract_b": {
                        "contract_id": b_id,
                        "question": b.get("question") or "",
                        "task_type": b.get("task_type") or "",
                        "horizon": b.get("horizon") or "",
                    },
                    "required_output_fields": REQUIRED_OUTPUT_FIELDS,
                    "scoring_endpoint": "pairwise_translation_tournament_utility",
                }
            )
            answer_key.append(
                {
                    "pair_id": pair_id,
                    "source": source,
                    "contract_id_a": a_id,
                    "contract_id_b": b_id,
                    "y_a": int(a["y_known"]),
                    "y_b": int(b["y_known"]),
                    "actual_delta": int(a["y_known"]) - int(b["y_known"]),
                }
            )

        nodes = set(contracts)
        comps = connected_components(nodes, graph_edges)
        source_reports[source] = {
            "contracts": len(contracts),
            "yes": sum(1 for c in contracts.values() if int(c["y_known"]) == 1),
            "no": sum(1 for c in contracts.values() if int(c["y_known"]) == 0),
            "pairs": len(edges),
            "degree_counts": dict(sorted(Counter(degree.values()).items())),
            "connected_components": len(comps),
            "largest_component": max((len(c) for c in comps), default=0),
            "a_yes": sum(1 for row in answer_key if row["source"] == source and row["y_a"] == 1),
            "a_no": sum(1 for row in answer_key if row["source"] == source and row["y_a"] == 0),
        }

    total_degree = Counter()
    for row in answer_key:
        total_degree[str(row["contract_id_a"])] += 1
        total_degree[str(row["contract_id_b"])] += 1
    report = {
        "packet": "f47_translation_tournament_packet",
        "date": "2026-06-03",
        "base_queue": str(queue_path),
        "base_answer_key": str(key_path),
        "dispatch_rows": len(dispatch),
        "unique_contracts": len(total_degree),
        "degree_counts": dict(sorted(Counter(total_degree.values()).items())),
        "non_tie_pairs_by_construction": sum(1 for row in answer_key if row["actual_delta"] != 0),
        "orientation_balance": {
            "a_yes": sum(1 for row in answer_key if row["y_a"] == 1),
            "a_no": sum(1 for row in answer_key if row["y_a"] == 0),
        },
        "source_reports": source_reports,
        "validity_note": (
            "This packet is not evidence until model calls are fired. It is designed "
            "to test whether F47 pairwise rankings can be translated into per-contract "
            "probability or review-allocation signals."
        ),
    }
    return dispatch, answer_key, report


def write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def write_report(report: dict[str, Any], path: Path, queue: Path, answer_key: Path) -> None:
    lines = [
        "# F47 translation tournament packet - 2026-06-03",
        "",
        "This is a packet skeleton, not fresh evidence. It reuses the resolved contracts from the first F47 source-balanced consumer packet but creates overlapping same-source opposite-outcome pairs so ranking-to-probability translation is identifiable.",
        "",
        f"- Dispatch rows: `{report['dispatch_rows']}`",
        f"- Unique contracts: `{report['unique_contracts']}`",
        f"- Non-tie pairs by construction: `{report['non_tie_pairs_by_construction']}`",
        f"- Degree counts: `{report['degree_counts']}`",
        f"- Orientation balance: A-YES `{report['orientation_balance']['a_yes']}`, A-NO `{report['orientation_balance']['a_no']}`",
        "",
        "## Source Graphs",
        "",
        "| source | contracts | yes | no | pairs | degree counts | components | largest | A-YES | A-NO |",
        "|---|---:|---:|---:|---:|---|---:|---:|---:|---:|",
    ]
    for source, row in report["source_reports"].items():
        lines.append(
            f"| {source} | {row['contracts']} | {row['yes']} | {row['no']} | {row['pairs']} | `{row['degree_counts']}` | {row['connected_components']} | {row['largest_component']} | {row['a_yes']} | {row['a_no']} |"
        )
    lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Dispatch queue: `{queue}`",
            f"- Answer key: `{answer_key}`",
            "",
            "Smallest valid use: run at least two held-out families on this overlapping packet, score pairwise utility, then fit a source-held-out Bradley-Terry/Thurstone/Elo-style translation and compare derived probabilities or review decisions against F100/raw/market controls. Do not infer Brier improvement from pairwise utility alone.",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-queue", type=Path, default=DEFAULT_BASE_QUEUE)
    parser.add_argument("--base-answer-key", type=Path, default=DEFAULT_BASE_KEY)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--answer-key", type=Path, default=DEFAULT_KEY)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    dispatch, answer_key, report = build_packet(args.base_queue, args.base_answer_key)
    write_jsonl(dispatch, args.queue)
    args.answer_key.write_text(json.dumps({"answer_key": answer_key, "report": report}, indent=2, sort_keys=True) + "\n")
    write_report(report, args.report, args.queue, args.answer_key)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
