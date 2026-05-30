#!/usr/bin/env python3
"""Inventory qualified source packets for the LeanMill entrance buffer.

This is a cheap source-qualification layer. It does not run Lean and it does
not grant proof credit. It scans existing internal candidate packets and NS
proof-search packets, then classifies each as replay-ready, contract-blocked,
practice/control, or obligation-only so the mill can source rows without
artisanal chat memory.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_ROOTS = [
    "analytics/public/leanmill",
    "projects/ns_millennium_hunt/workspace",
]
DEFAULT_OUT = "analytics/public/leanmill/dashboard_data/source_inventory.json"
DEFAULT_MD = "analytics/public/leanmill/dashboard_data/source_inventory.md"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        obj = json.loads(path.read_text(errors="ignore"))
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def _iter_candidate_files(roots: list[Path]) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            name = p.name.lower()
            if p.suffix == ".json" and ("candidate" in name or "canary" in name or "source" in name):
                out.append(p)
            elif p.suffix == ".md" and ("proofsearch_packet" in name or "proof-search" in name):
                out.append(p)
    return sorted(set(out))


def _as_list(x: Any) -> list[Any]:
    return x if isinstance(x, list) else []


def _rows(obj: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("rows", "source_discovery_queue", "packets"):
        val = obj.get(key)
        if isinstance(val, list):
            return [r for r in val if isinstance(r, dict)]
    if isinstance(obj.get("row"), dict):
        return [obj["row"]]
    return []


def _candidate_list(row: dict[str, Any]) -> list[dict[str, Any]]:
    vals: list[Any] = []
    for key in (
        "candidates",
        "usable_candidates",
        "canary_ready_candidates",
        "row_context_ready_candidates",
        "ready_candidates",
    ):
        vals.extend(_as_list(row.get(key)))
    return [c for c in vals if isinstance(c, dict)]


def _extract_hinges_from_candidate(c: dict[str, Any]) -> list[str]:
    hinges: list[str] = []
    for key in ("source_hinges", "available_source_names"):
        val = c.get(key)
        if isinstance(val, list):
            hinges.extend(str(v) for v in val[:6])
    for key in ("name", "candidate_source", "source_lane", "candidate_action", "tactic"):
        val = c.get(key)
        if isinstance(val, str) and val.strip():
            hinges.append(val.strip().splitlines()[0][:160])
    return hinges


def _top_hinges(rows: list[dict[str, Any]], limit: int = 8) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for row in rows:
        for c in _candidate_list(row):
            for h in _extract_hinges_from_candidate(c):
                if h not in seen:
                    seen.add(h)
                    out.append(h)
                if len(out) >= limit:
                    return out
    return out


def _has_recursive_key(obj: Any, key: str) -> bool:
    if isinstance(obj, dict):
        return any(k == key or _has_recursive_key(v, key) for k, v in obj.items())
    if isinstance(obj, list):
        return any(_has_recursive_key(v, key) for v in obj)
    return False


def _has_recursive_value(obj: Any, needle: str) -> bool:
    if isinstance(obj, str):
        return needle in obj
    if isinstance(obj, dict):
        return any(_has_recursive_value(v, needle) for v in obj.values())
    if isinstance(obj, list):
        return any(_has_recursive_value(v, needle) for v in obj)
    return False


def _count_candidates(rows: list[dict[str, Any]]) -> int:
    return sum(len(_candidate_list(r)) for r in rows)


def _classify_json(path: Path, obj: dict[str, Any]) -> dict[str, Any]:
    rows = _rows(obj)
    candidate_count = _count_candidates(rows)
    metrics = obj.get("metrics") if isinstance(obj.get("metrics"), dict) else {}
    decision = obj.get("decision") if isinstance(obj.get("decision"), dict) else {}
    status = str(obj.get("status") or "")
    replay_executed = bool(metrics.get("replay_executed") or obj.get("replay_executed"))
    no_replay = bool(metrics.get("no_replay_or_training") or decision.get("run_replay_now") is False)
    requires_gp230 = _has_recursive_key(obj, "requires_gp230_before_replay") or bool(
        decision.get("forecast_pool_contract_id") or obj.get("forecast_pool_contract_id")
    )
    source_safe = not bool(metrics.get("target_theorem_self_reference_used")) and not bool(
        metrics.get("target_proof_lines_used_for_candidate_generation")
    )
    exact_target_blocked = bool(metrics.get("target_theorem_self_reference_used"))
    practice = "practice" in str(obj).lower() or "control" in path.name.lower()

    if exact_target_blocked:
        eligibility = "blocked_exact_target_or_gold_leak"
    elif requires_gp230:
        eligibility = "contract_blocked_before_replay"
    elif candidate_count and source_safe and not replay_executed:
        eligibility = "source_intake_candidate"
    elif candidate_count and replay_executed:
        eligibility = "historical_replay_artifact"
    elif no_replay:
        eligibility = "packet_only_no_replay"
    else:
        eligibility = "needs_manual_triage"
    if practice and eligibility == "source_intake_candidate":
        eligibility = "practice_control_only"

    return {
        "path": str(path),
        "sha256": _sha(path),
        "kind": "json_candidate_packet",
        "status": status or None,
        "row_count": len(rows),
        "candidate_count": candidate_count,
        "eligibility": eligibility,
        "source_safe": source_safe,
        "requires_gp230_or_forecast": requires_gp230,
        "replay_executed": replay_executed,
        "no_replay_declared": no_replay,
        "top_hinges": _top_hinges(rows),
    }


_NUMBERED_RE = re.compile(r"^\s*\d+\.\s+\*\*(?P<title>[^*]+)\*\*", re.MULTILINE)
_BULLET_RE = re.compile(r"^\s*[-*]\s+`?(?P<item>[-A-Za-z0-9_./:' ]{8,120})`?", re.MULTILINE)


def _classify_md(path: Path) -> dict[str, Any]:
    text = path.read_text(errors="ignore")
    obligations = [m.group("title").strip() for m in _NUMBERED_RE.finditer(text)]
    artifacts = []
    for m in _BULLET_RE.finditer(text):
        item = m.group("item").strip()
        if item.endswith(".lean") or "obligation" in item.lower() or "target" in item.lower():
            artifacts.append(item)
    return {
        "path": str(path),
        "sha256": _sha(path),
        "kind": "ns_proofsearch_obligation_packet",
        "status": "obligation_packet_only",
        "row_count": 0,
        "candidate_count": len(obligations),
        "eligibility": "obligation_only_needs_theorem_shaping",
        "source_safe": True,
        "requires_gp230_or_forecast": False,
        "replay_executed": False,
        "no_replay_declared": True,
        "top_hinges": obligations[:8] or artifacts[:8],
        "referenced_artifacts": artifacts[:12],
    }


def _summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    by_elig: dict[str, int] = {}
    candidates_by_elig: dict[str, int] = {}
    for item in items:
        elig = str(item.get("eligibility"))
        by_elig[elig] = by_elig.get(elig, 0) + 1
        candidates_by_elig[elig] = candidates_by_elig.get(elig, 0) + int(item.get("candidate_count") or 0)
    source_candidates = [
        i for i in items if i.get("eligibility") in {"source_intake_candidate", "practice_control_only"}
    ]
    return {
        "artifacts_scanned": len(items),
        "by_eligibility": by_elig,
        "candidate_count_by_eligibility": candidates_by_elig,
        "source_intake_artifacts": len([i for i in items if i.get("eligibility") == "source_intake_candidate"]),
        "source_intake_candidate_count": sum(int(i.get("candidate_count") or 0) for i in source_candidates),
        "contract_blocked_artifacts": len([i for i in items if i.get("eligibility") == "contract_blocked_before_replay"]),
        "obligation_only_artifacts": len([i for i in items if i.get("eligibility") == "obligation_only_needs_theorem_shaping"]),
    }


def build_inventory(args: argparse.Namespace) -> dict[str, Any]:
    roots = [Path(p) for p in args.roots]
    items: list[dict[str, Any]] = []
    for path in _iter_candidate_files(roots):
        if args.max_files and len(items) >= args.max_files:
            break
        if path.suffix == ".json":
            obj = _read_json(path)
            if obj is None:
                continue
            item = _classify_json(path, obj)
        else:
            item = _classify_md(path)
        if int(item.get("candidate_count") or 0) == 0 and not args.include_empty:
            continue
        items.append(item)
    items.sort(key=lambda x: (str(x.get("eligibility")), -int(x.get("candidate_count") or 0), str(x.get("path"))))
    payload = {
        "schema": "leanmill-source-inventory-v1",
        "generated_at": _now(),
        "roots": [str(r) for r in roots],
        "summary": _summarize(items),
        "items": items,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if args.md:
        Path(args.md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.md).write_text(_render_md(payload) + "\n")
    return payload


def _render_md(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    lines = [
        "# LeanMill Source Inventory",
        "",
        f"Generated: `{payload['generated_at']}`",
        "",
        "## Summary",
        "",
        f"- Artifacts scanned: `{s['artifacts_scanned']}`",
        f"- Source-intake artifacts: `{s['source_intake_artifacts']}`",
        f"- Source/practice candidate count: `{s['source_intake_candidate_count']}`",
        f"- Contract-blocked artifacts: `{s['contract_blocked_artifacts']}`",
        f"- Obligation-only packets: `{s['obligation_only_artifacts']}`",
        "",
        "## Eligibility Mix",
        "",
        "| Eligibility | Artifacts | Candidates |",
        "|---|---:|---:|",
    ]
    for elig, n in sorted(s["by_eligibility"].items()):
        lines.append(f"| `{elig}` | {n} | {s['candidate_count_by_eligibility'].get(elig, 0)} |")
    lines.extend(["", "## Top Source Intake Artifacts", "", "| Artifact | Rows | Candidates | Hinges |", "|---|---:|---:|---|"])
    rows = [i for i in payload["items"] if i.get("eligibility") in {"source_intake_candidate", "practice_control_only"}]
    for item in rows[:30]:
        hinges = "<br>".join(f"`{h}`" for h in (item.get("top_hinges") or [])[:4])
        lines.append(f"| `{item['path']}` | {item['row_count']} | {item['candidate_count']} | {hinges} |")
    lines.extend(["", "## Contract-Blocked Replay Candidates", "", "| Artifact | Rows | Candidates | Hinges |", "|---|---:|---:|---|"])
    for item in [i for i in payload["items"] if i.get("eligibility") == "contract_blocked_before_replay"][:20]:
        hinges = "<br>".join(f"`{h}`" for h in (item.get("top_hinges") or [])[:4])
        lines.append(f"| `{item['path']}` | {item['row_count']} | {item['candidate_count']} | {hinges} |")
    lines.extend(["", "## NS Obligation Packets", "", "| Artifact | Obligations | Top obligations |", "|---|---:|---|"])
    for item in [i for i in payload["items"] if i.get("eligibility") == "obligation_only_needs_theorem_shaping"][:20]:
        hinges = "<br>".join(f"`{h}`" for h in (item.get("top_hinges") or [])[:4])
        lines.append(f"| `{item['path']}` | {item['candidate_count']} | {hinges} |")
    return "\n".join(lines)


def _self_test() -> int:
    row = {
        "candidates": [
            {
                "source_hinges": ["Foo.bar"],
                "tactic": "exact Foo.bar",
                "requires_gp230_before_replay": True,
            }
        ]
    }
    obj = {"rows": [row], "decision": {"run_replay_now": False}}
    tmp = Path("/tmp/leanmill_source_inventory_selftest.json")
    tmp.write_text(json.dumps(obj))
    item = _classify_json(tmp, obj)
    assert item["candidate_count"] == 1, item
    assert item["eligibility"] == "contract_blocked_before_replay", item
    assert item["top_hinges"][0] == "Foo.bar", item
    tmp.unlink(missing_ok=True)
    print("leanmill_source_inventory self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", nargs="+", default=DEFAULT_ROOTS)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--md", default=DEFAULT_MD)
    ap.add_argument("--max-files", type=int, default=0)
    ap.add_argument("--include-empty", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    payload = build_inventory(args)
    print(json.dumps(payload["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
