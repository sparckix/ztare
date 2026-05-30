#!/usr/bin/env python3
"""Score Path-C residual basins with cheap temporal/local signals.

This is a Base3-style non-neural baseline for the A/B/C program:
combine recurrence, node/action popularity, and local co-occurrence
before spending solver budget. It is deliberately advisory. It never
claims proof progress and never calls Lean, Codex, or the network.
"""
from __future__ import annotations

import argparse
import json
import re
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_QUEUE = "analytics/public/leanmill/path_curricula/PATH_C_CURRICULUM_QUEUE.json"
DEFAULT_RESIDUAL_LEDGER = "analytics/public/ledgers/residual_to_lever/RUNG1_RESIDUAL_LEDGER.jsonl"
DEFAULT_PATTERN_LEDGER = "analytics/public/ledgers/pattern_deployment/pattern_deployment_ledger.jsonl"
DEFAULT_NS_MANIFEST = "projects/ns_millennium_hunt/workspace/ns_residual_manifest.md"
DEFAULT_OUT = "analytics/public/leanmill/path_curricula/PATH_C_TEMPORAL_BASIN_SCORE.json"
DEFAULT_MD = "analytics/public/leanmill/path_curricula/PATH_C_TEMPORAL_BASIN_SCORE.md"

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_+\-/]{2,}")
DATE_RE = re.compile(r"20\d\d-\d\d-\d\d")
CANONICAL_RE = re.compile(r"^\|\s*(?:\*\*)?([A-Z]+\d+|[A-Z]{1,3}|G\d+–G\d+)(?:\*\*)?\s*\|\s*(?:\*\*)?([^|*]+)")
ALIAS_RE = re.compile(r"^- `([^`]+)`")
TICK_RE = re.compile(r"\btick(\d+)\b", re.I)
STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "only",
    "does", "not", "cannot", "before", "after", "because", "under", "over",
    "than", "then", "now", "row", "rows", "next", "claim", "claims",
    "source", "artifact", "baseline", "model", "diagnostic", "queue",
}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(errors="ignore"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(errors="ignore").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _tokens(*parts: Any) -> set[str]:
    text = " ".join(str(p or "") for p in parts)
    return {t.lower() for t in TOKEN_RE.findall(text)
            if len(t) >= 3 and t.lower() not in STOPWORDS
            and not t.lower().startswith("http")}


def _event(source: str, row_id: str, next_lever: str, outcome: str,
           text: str, ts: str = "") -> dict[str, Any]:
    return {
        "source": source,
        "row_id": row_id,
        "next_lever": next_lever,
        "outcome": outcome,
        "ts": ts,
        "tokens": sorted(_tokens(row_id, next_lever, outcome, text)),
        "text": text[:500],
    }


def _events_from_residual_ledger(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for rec in _read_jsonl(path):
        row_id = str(rec.get("row") or rec.get("row_id") or "")
        if not row_id:
            continue
        residual = str(rec.get("residual_class") or "unknown_residual")
        lever = str(rec.get("next_lever") or "classify_residual")
        outcome = "certified_proof_exists" if rec.get("certified_proof_exists") else residual
        events.append(_event(
            "residual_to_lever",
            row_id,
            lever,
            outcome,
            " ".join(str(rec.get(k) or "") for k in ("next_target", "scoreboard", "run")),
            str(rec.get("ts") or ""),
        ))
    return events


def _events_from_pattern_ledger(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for rec in _read_jsonl(path):
        substrate = str(rec.get("substrate") or "")
        if "GP-225" not in substrate and "NS-" not in substrate:
            continue
        row_id = str(rec.get("task_id") or rec.get("dispatch_id") or substrate)
        primary = str(rec.get("primary_pattern") or "unknown_pattern")
        secondaries = ",".join(str(x) for x in (rec.get("secondary_patterns") or []))
        outcome = str(rec.get("outcome_bucket_realized") or "outcome_unknown")
        text = " ".join(str(rec.get(k) or "") for k in (
            "substrate", "outcome_bucket_pre_registered", "outcome_bucket_realized", "notes"))
        events.append(_event(
            "pattern_deployment",
            row_id,
            primary,
            outcome,
            secondaries + " " + text,
            str(rec.get("dispatched_at") or ""),
        ))
    return events


def _parse_ns_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"canonical_nodes": [], "aliases": [], "events": []}
    aliases: list[dict[str, Any]] = []
    canonical_nodes: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    section = ""
    for line in path.read_text(errors="ignore").splitlines():
        if line.startswith("## "):
            section = line.strip("# ").strip()
        m = CANONICAL_RE.match(line)
        if m:
            node = m.group(1).replace("**", "").strip()
            name = m.group(2).replace("**", "").strip()
            canonical_nodes.append({"node": node, "name": name, "section": section})
            events.append(_event("ns_manifest_node", node, "canonical_node_open", "open", name))
        a = ALIAS_RE.match(line)
        if a:
            alias = a.group(1).strip()
            ticks = TICK_RE.findall(line)
            dates = DATE_RE.findall(line)
            target_node = "C5" if "Alias table" in section or "map to C5" in section else "unknown"
            aliases.append({
                "alias": alias,
                "target_node": target_node,
                "ticks": ticks,
                "dates": dates,
                "section": section,
            })
            events.append(_event(
                "ns_manifest_alias",
                target_node,
                "anti_rehash_gate",
                "recurrence_alias",
                alias + " " + line,
                dates[-1] if dates else "",
            ))
    return {"canonical_nodes": canonical_nodes, "aliases": aliases, "events": events}


def _queue_candidates(path: Path) -> list[dict[str, Any]]:
    obj = _read_json(path)
    rows = obj.get("rows") or []
    return [r for r in rows if str(r.get("kind") or "") not in {"path_c_ratified_candidate"}]


def _base3_score(candidate: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    row_id = str(candidate.get("row_id") or "")
    lever = str(candidate.get("next_lever") or "")
    cand_tokens = _tokens(row_id, lever, candidate.get("reason"), candidate.get("residual_class"))
    recurrence = sum(1 for e in events if e["row_id"] == row_id or row_id in e["tokens"])
    lever_popularity = sum(1 for e in events if e["next_lever"] == lever)
    token_hits = Counter()
    for e in events:
        overlap = cand_tokens & set(e["tokens"])
        for tok in overlap:
            token_hits[tok] += 1
    local_cooccurrence = sum(token_hits.values())
    positive_support = sum(
        1 for e in events
        if cand_tokens & set(e["tokens"])
        and e["outcome"] in {"certified_proof_exists", "recurrence_alias", "open"}
    )
    recurrence_penalty = min(recurrence, 10) * 0.25
    score = 0.8 * lever_popularity + 0.5 * local_cooccurrence + 0.4 * positive_support - recurrence_penalty
    return {
        "row_id": row_id,
        "kind": candidate.get("kind"),
        "next_lever": lever,
        "score": round(score, 3),
        "components": {
            "recurrence": recurrence,
            "lever_popularity": lever_popularity,
            "local_cooccurrence": local_cooccurrence,
            "positive_support": positive_support,
            "recurrence_penalty": round(recurrence_penalty, 3),
        },
        "top_overlap_tokens": [tok for tok, _ in token_hits.most_common(8)],
        "advisory": _candidate_advisory(candidate, recurrence),
    }


def _candidate_advisory(candidate: dict[str, Any], recurrence: int) -> str:
    kind = str(candidate.get("kind") or "")
    if kind == "historical_contract_cleanup":
        return "cleanup_only_do_not_spend_solver_budget"
    if kind == "typed_label_diagnostic_completed":
        return "data_acquisition_only_no_model_claim"
    if recurrence >= 3:
        return "high_recurrence_require_escape_mechanism_before_budget"
    return "eligible_for_one_row_smoke_if_pre_registered"


def score(queue: Path, residual_ledger: Path, pattern_ledger: Path,
          ns_manifest: Path, out: Path | None = None,
          markdown: Path | None = None) -> dict[str, Any]:
    ns = _parse_ns_manifest(ns_manifest)
    events = []
    events.extend(_events_from_residual_ledger(residual_ledger))
    events.extend(_events_from_pattern_ledger(pattern_ledger))
    events.extend(ns["events"])
    candidates = _queue_candidates(queue)
    scored = sorted(
        [_base3_score(c, events) for c in candidates],
        key=lambda r: (-float(r["score"]), str(r["row_id"])),
    )
    alias_by_node = Counter(str(a["target_node"]) for a in ns["aliases"])
    ns_summary = {
        "canonical_node_count": len(ns["canonical_nodes"]),
        "alias_count": len(ns["aliases"]),
        "alias_count_by_node": dict(sorted(alias_by_node.items())),
        "top_alias_tokens": [
            tok for tok, _ in Counter(
                t for a in ns["aliases"] for t in _tokens(a["alias"])
            ).most_common(20)
        ],
        "advisory": (
            "NS basin graph should gate budget: C5-alias-like proposals require "
            "a named escape mechanism before any solver/model spend."
        ),
    }
    out_obj = {
        "schema": "path-c-temporal-basin-score-v1",
        "inputs": {
            "queue": str(queue),
            "residual_ledger": str(residual_ledger),
            "pattern_ledger": str(pattern_ledger),
            "ns_manifest": str(ns_manifest),
        },
        "event_count": len(events),
        "candidate_count": len(candidates),
        "scored_candidates": scored,
        "ns_basin_summary": ns_summary,
        "decision": {
            "accelerate_without_confounders": True,
            "method": "use temporal/local advisory for triage only; proof/gap claims still require Path-B governance",
            "next_highest_yield": (
                "new source-safe canary acquisition for GP225; NS budget only for proposals "
                "that pass the anti-rehash escape-mechanism gate"
            ),
        },
    }
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(out_obj, indent=2, sort_keys=True) + "\n")
    if markdown:
        _write_md(out_obj, markdown)
    return out_obj


def _write_md(obj: dict[str, Any], path: Path) -> None:
    lines = [
        "# Path C Temporal Basin Score",
        "",
        f"Events: `{obj['event_count']}`",
        f"Candidates: `{obj['candidate_count']}`",
        "",
        "## Candidate Advisory",
        "",
        "| Rank | Row | Kind | Next Lever | Score | Advisory |",
        "|---:|---|---|---|---:|---|",
    ]
    for i, row in enumerate(obj["scored_candidates"][:20], start=1):
        lines.append(
            f"| {i} | `{row['row_id']}` | {row['kind']} | `{row['next_lever']}` | "
            f"{row['score']} | {row['advisory']} |"
        )
    ns = obj["ns_basin_summary"]
    lines.extend([
        "",
        "## NS Basin",
        "",
        f"Canonical nodes: `{ns['canonical_node_count']}`",
        f"Aliases: `{ns['alias_count']}`",
        f"Alias count by node: `{ns['alias_count_by_node']}`",
        "",
        f"Advisory: {ns['advisory']}",
        "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))


def self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        queue = root / "queue.json"
        residual = root / "residual.jsonl"
        pattern = root / "pattern.jsonl"
        ns = root / "ns.md"
        queue.write_text(json.dumps({"rows": [
            {"row_id": "r1", "kind": "typed_label_diagnostic_completed", "next_lever": "acquire_rank1_negative"},
            {"row_id": "r2", "kind": "path_c_ratified_candidate", "next_lever": "retire"},
        ]}))
        residual.write_text(json.dumps({
            "row": "r1",
            "residual_class": "missing_library_premise",
            "next_lever": "acquire_rank1_negative",
            "certified_proof_exists": False,
        }) + "\n")
        pattern.write_text(json.dumps({
            "dispatch_id": "d1",
            "substrate": "NS-Track-B",
            "primary_pattern": "PATTERN-018",
            "outcome_bucket_realized": "recurrence",
            "notes": "strict margin alias",
        }) + "\n")
        ns.write_text("""# NS
## Canonical open nodes
| C5 | Constantin-Fefferman | OPEN |
## Alias table -- map to C5
- `strict-margin certificate` (2026-05-12)
""")
        obj = score(queue, residual, pattern, ns)
        assert obj["candidate_count"] == 1, obj
        assert obj["scored_candidates"][0]["row_id"] == "r1", obj
        assert obj["ns_basin_summary"]["alias_count_by_node"]["C5"] == 1, obj
    print("path_c_temporal_basin_scorer self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", default=DEFAULT_QUEUE)
    ap.add_argument("--residual-ledger", default=DEFAULT_RESIDUAL_LEDGER)
    ap.add_argument("--pattern-ledger", default=DEFAULT_PATTERN_LEDGER)
    ap.add_argument("--ns-manifest", default=DEFAULT_NS_MANIFEST)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--markdown", default=DEFAULT_MD)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    obj = score(
        Path(args.queue),
        Path(args.residual_ledger),
        Path(args.pattern_ledger),
        Path(args.ns_manifest),
        Path(args.out) if args.out else None,
        Path(args.markdown) if args.markdown else None,
    )
    print(json.dumps({
        "out": args.out,
        "markdown": args.markdown,
        "event_count": obj["event_count"],
        "candidate_count": obj["candidate_count"],
        "ns_alias_count": obj["ns_basin_summary"]["alias_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
