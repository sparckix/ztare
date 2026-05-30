#!/usr/bin/env python3
"""LeanSearch candidate-source adapter for Path C.

This de-artisanalizes premise/source discovery while preserving the
science boundary:
  - never persist LeanSearch proof bodies (`value`)
  - exclude exact-target declarations by default
  - mark same-module non-target results as requiring source-order check
  - emit candidate-source packets only; no Lean replay, no labels, no training
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_SOURCE_QUEUE = "analytics/public/leanmill/results/v2061_public_union_next_source_discovery_queue.json"
DEFAULT_OUT = "analytics/public/leanmill/leansearch/LEANSEARCH_SOURCE_CANDIDATE_PACKET.json"
DEFAULT_MD = "analytics/public/leanmill/leansearch/LEANSEARCH_SOURCE_CANDIDATE_PACKET.md"
DEFAULT_ENDPOINT = "https://leansearch.net/search"
DEFAULT_MATHLIB_ROOT = (
    "analytics/public/leanmill/external_benchmarks/sandboxes/"
    "v28A_carleson_baseline/carleson/.lake/packages/mathlib"
)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(errors="ignore"))


def _sha(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _module_from_source_file(source_file: str | None) -> str:
    if not source_file:
        return ""
    s = source_file.removesuffix(".lean").replace("/", ".")
    return s


def _dotted(parts: Any) -> str:
    if isinstance(parts, list):
        return ".".join(str(p) for p in parts)
    return str(parts or "")


def _row_query(row: dict[str, Any]) -> str:
    pieces = [
        row.get("theorem"),
        row.get("source_hinge"),
        row.get("non_timeout_candidate_family"),
    ]
    names = row.get("available_source_names") or []
    if names:
        pieces.append(" ".join(str(n) for n in names[:6]))
    return " ".join(str(p) for p in pieces if p)


def _post_json(endpoint: str, body: dict[str, Any], timeout: float = 30.0,
               retries: int = 0, retry_sleep: float = 30.0) -> Any:
    raw = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=raw,
        headers={"Content-Type": "application/json", "User-Agent": "ztare-path-c-leansearch-adapter/1.0"},
        method="POST",
    )
    attempt = 0
    while True:
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt >= retries:
                raise
            retry_after = exc.headers.get("Retry-After")
            sleep_s = retry_sleep
            if retry_after:
                try:
                    sleep_s = max(sleep_s, float(retry_after))
                except ValueError:
                    pass
            time.sleep(sleep_s)
            attempt += 1


def _decl_line_index(source_path: Path) -> dict[str, int]:
    if not source_path.exists():
        return {}
    out: dict[str, int] = {}
    prefixes = ("theorem ", "lemma ", "def ", "abbrev ", "instance ")
    for i, line in enumerate(source_path.read_text(errors="ignore").splitlines(), start=1):
        stripped = line.strip()
        if not stripped.startswith(prefixes):
            continue
        parts = stripped.replace("(", " ").replace("{", " ").replace("[", " ").split()
        if len(parts) >= 2:
            name = parts[1].split(":")[0]
            out.setdefault(name, i)
    return out


def _source_order_status(name: str, target_name: str, source_file: str | None,
                         mathlib_root: Path | None) -> dict[str, Any]:
    if not source_file or not mathlib_root:
        return {"source_order_status": "not_checked", "candidate_line": None, "target_line": None}
    idx = _decl_line_index(mathlib_root / source_file)
    cand_short = name.split(".")[-1]
    target_short = target_name.split(".")[-1]
    cand_line = idx.get(cand_short)
    target_line = idx.get(target_short)
    if cand_line is None or target_line is None:
        status = "source_order_unknown"
    elif cand_line < target_line:
        status = "before_target_source_safe"
    elif cand_line > target_line:
        status = "post_target_same_file_forbidden"
    else:
        status = "same_decl_exact_target"
    return {"source_order_status": status, "candidate_line": cand_line, "target_line": target_line}


def _normalize_result(item: dict[str, Any], target_name: str, source_module: str,
                      source_file: str | None, mathlib_root: Path | None) -> dict[str, Any]:
    result = item.get("result") or {}
    module_name = _dotted(result.get("module_name"))
    name = _dotted(result.get("name"))
    exact_target = bool(target_name and name.split(".")[-1] == target_name.split(".")[-1])
    same_module = bool(source_module and module_name == source_module)
    order = _source_order_status(name, target_name, source_file, mathlib_root) if same_module else {
        "source_order_status": "not_same_module",
        "candidate_line": None,
        "target_line": None,
    }
    if exact_target:
        safety = "excluded_exact_target"
    elif order["source_order_status"] == "before_target_source_safe":
        safety = "non_target_same_module_before_target"
    elif order["source_order_status"] == "post_target_same_file_forbidden":
        safety = "post_target_same_file_forbidden"
    elif same_module:
        safety = "non_target_same_module_requires_source_order_check"
    else:
        safety = "non_target_external_module_candidate"
    return {
        "name": name,
        "module_name": module_name,
        "kind": result.get("kind"),
        "signature": result.get("signature"),
        "type": result.get("type"),
        "informal_name": result.get("informal_name"),
        "informal_description": result.get("informal_description"),
        "distance": item.get("distance"),
        "doc_url": f"https://leanprover-community.github.io/mathlib4_docs/find/?pattern={name}#doc" if name else None,
        "candidate_action_templates": [
            f"exact {name}",
            f"apply {name}",
            f"simpa using {name}",
        ] if name and not exact_target else [],
        "source_safety_status": safety,
        "source_order_status": order["source_order_status"],
        "candidate_line": order["candidate_line"],
        "target_line": order["target_line"],
        "requires_source_order_check": bool(
            same_module
            and not exact_target
            and order["source_order_status"] not in {"before_target_source_safe", "post_target_same_file_forbidden"}
        ),
        "source_order_safe": bool(order["source_order_status"] == "before_target_source_safe"),
        "post_target_forbidden": bool(order["source_order_status"] == "post_target_same_file_forbidden"),
        "proof_body_persisted": False,
        "exact_target_excluded": exact_target,
    }


def _normalize_response(raw: Any, row: dict[str, Any], limit: int,
                        mathlib_root: Path | None) -> dict[str, Any]:
    target_name = str(row.get("theorem") or row.get("row_id") or "")
    source_module = _module_from_source_file(row.get("source_file"))
    bucket = raw[0] if isinstance(raw, list) and raw and isinstance(raw[0], list) else raw
    if not isinstance(bucket, list):
        bucket = []
    normalized = [
        _normalize_result(item, target_name, source_module, row.get("source_file"), mathlib_root)
        for item in bucket[:limit]
    ]
    exact_excluded = [r for r in normalized if r["exact_target_excluded"]]
    post_target = [r for r in normalized if r["post_target_forbidden"]]
    usable = [r for r in normalized if not r["exact_target_excluded"] and not r["post_target_forbidden"]]
    return {
        "row_id": row.get("row_id"),
        "theorem": row.get("theorem"),
        "source_file": row.get("source_file"),
        "source_module": source_module,
        "query": _row_query(row),
        "retrieved_total": len(normalized),
        "exact_target_excluded_count": len(exact_excluded),
        "usable_candidate_count": len(usable),
        "post_target_forbidden_count": len(post_target),
        "usable_candidates": usable,
        "excluded_exact_targets": exact_excluded,
        "excluded_post_target_candidates": post_target,
        "source_policy": {
            "leansearch_value_field_persisted": False,
            "exact_target_declarations_excluded": True,
            "same_module_results_require_source_order_check": True,
            "post_target_same_file_declarations_excluded": True,
            "candidate_packet_only_no_replay": True,
        },
    }


def _rows_from_source_queue(path: Path, max_rows: int | None = None) -> list[dict[str, Any]]:
    obj = _read_json(path)
    rows = list(obj.get("source_discovery_queue") or [])
    if max_rows is not None:
        rows = rows[:max_rows]
    return rows


def _packet_payload(packets: list[dict[str, Any]], endpoint: str, fixture: Path | None,
                    status_note: str = "") -> dict[str, Any]:
    usable_total = sum(int(p["usable_candidate_count"]) for p in packets)
    exact_excluded_total = sum(int(p["exact_target_excluded_count"]) for p in packets)
    post_target_total = sum(int(p["post_target_forbidden_count"]) for p in packets)
    order_check_total = sum(
        1 for p in packets for r in p["usable_candidates"]
        if r["requires_source_order_check"]
    )
    source_order_safe_total = sum(
        1 for p in packets for r in p["usable_candidates"]
        if r["source_order_safe"]
    )
    return {
        "schema": "leansearch-source-candidate-packet-v1",
        "generated_at": _now(),
        "endpoint": endpoint if not fixture else "fixture",
        "row_count": len(packets),
        "usable_candidate_total": usable_total,
        "exact_target_excluded_total": exact_excluded_total,
        "post_target_forbidden_total": post_target_total,
        "same_module_order_check_total": order_check_total,
        "same_module_before_target_total": source_order_safe_total,
        "status": status_note or ("candidate_sources_found" if usable_total else "no_candidate_sources_found"),
        "source_policy": {
            "no_proof_bodies_persisted": True,
            "exact_targets_excluded": True,
            "same_module_order_check_required": True,
            "post_target_same_file_excluded": True,
            "path_b_required_before_any_closure_credit": True,
            "no_replay_or_training": True,
        },
        "rows": packets,
        "decision": {
            "run_lean_replay_now": False,
            "train_model_now": False,
            "next_artifact": "static_filter_leansearch_candidates_then_one_row_canary_smoke",
        },
    }


def _write_outputs(payload: dict[str, Any], out: Path | None, markdown: Path | None) -> None:
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if markdown:
        _write_md(payload, markdown)


def build(rows: list[dict[str, Any]], endpoint: str, limit: int,
          out: Path | None = None, markdown: Path | None = None,
          fixture: Path | None = None,
          mathlib_root: Path | None = None,
          retries: int = 0,
          retry_sleep: float = 30.0,
          request_sleep: float = 0.0) -> dict[str, Any]:
    packets: list[dict[str, Any]] = []
    fixture_obj = _read_json(fixture) if fixture else {}
    for i, row in enumerate(rows):
        if fixture_obj:
            raw = fixture_obj.get(str(row.get("row_id"))) or fixture_obj.get("raw") or []
        else:
            raw = _post_json(
                endpoint,
                {"query": [_row_query(row)], "num_results": limit},
                retries=retries,
                retry_sleep=retry_sleep,
            )
        packets.append(_normalize_response(raw, row, limit, mathlib_root))
        _write_outputs(_packet_payload(packets, endpoint, fixture, "partial_candidate_sources_found"), out, markdown)
        if request_sleep and not fixture_obj and i < len(rows) - 1:
            time.sleep(request_sleep)

    payload = _packet_payload(packets, endpoint, fixture)
    _write_outputs(payload, out, markdown)
    return payload


def _write_md(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# LeanSearch Source Candidate Packet",
        "",
        f"Rows: `{payload['row_count']}`",
        f"Usable candidates: `{payload['usable_candidate_total']}`",
        f"Exact targets excluded: `{payload['exact_target_excluded_total']}`",
        f"Post-target same-file excluded: `{payload['post_target_forbidden_total']}`",
        f"Same-module before-target safe: `{payload['same_module_before_target_total']}`",
        f"Same-module order checks owed: `{payload['same_module_order_check_total']}`",
        "",
        "| Row | Query | Usable | Top Candidates |",
        "|---|---|---:|---|",
    ]
    for row in payload["rows"]:
        names = ", ".join(f"`{r['name']}`" for r in row["usable_candidates"][:5])
        query = str(row["query"]).replace("|", "/")[:120]
        lines.append(f"| `{row['row_id']}` | {query} | {row['usable_candidate_count']} | {names} |")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))


def _self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        fixture = root / "fixture.json"
        out = root / "out.json"
        md = root / "out.md"
        row = {
            "row_id": "r1",
            "theorem": "bayesRisk_lt_top",
            "source_file": "Mathlib/Probability/Decision/Risk/Basic.lean",
            "source_hinge": "bayesRisk finite",
        }
        fixture.write_text(json.dumps({
            "r1": [[
                {"result": {
                    "module_name": ["Mathlib", "Probability", "Decision", "Risk", "Basic"],
                    "name": ["ProbabilityTheory", "bayesRisk_lt_top"],
                    "kind": "theorem",
                    "signature": "target sig",
                    "type": "target type",
                    "value": ":= by exact bad_leak",
                }, "distance": 0.1},
                {"result": {
                    "module_name": ["Mathlib", "Probability", "Decision", "Risk", "Basic"],
                    "name": ["ProbabilityTheory", "bayesRisk_le_mul'"],
                    "kind": "theorem",
                    "signature": "source sig",
                    "type": "source type",
                    "value": ":= by exact also_not_persisted",
                }, "distance": 0.2},
            ]]
        }))
        mathlib = root / "mathlib"
        source = mathlib / "Mathlib/Probability/Decision/Risk/Basic.lean"
        source.parent.mkdir(parents=True)
        source.write_text("""
theorem bayesRisk_le_mul' : True := by trivial
theorem bayesRisk_lt_top : True := by trivial
theorem avgRisk_const_right : True := by trivial
""")
        obj = build([row], DEFAULT_ENDPOINT, 5, out, md, fixture, mathlib)
        assert obj["row_count"] == 1, obj
        assert obj["exact_target_excluded_total"] == 1, obj
        assert obj["usable_candidate_total"] == 1, obj
        text = out.read_text()
        assert "bad_leak" not in text and "also_not_persisted" not in text, text
        assert obj["rows"][0]["usable_candidates"][0]["source_order_safe"] is True
    print("leansearch_source_adapter self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-queue", default=DEFAULT_SOURCE_QUEUE)
    ap.add_argument("--query", action="append", default=[])
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--max-rows", type=int, default=None)
    ap.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--retry-sleep", type=float, default=45.0)
    ap.add_argument("--request-sleep", type=float, default=1.0)
    ap.add_argument("--fixture")
    ap.add_argument("--mathlib-root", default=DEFAULT_MATHLIB_ROOT)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--markdown", default=DEFAULT_MD)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    rows = _rows_from_source_queue(Path(args.source_queue), args.max_rows)
    for i, q in enumerate(args.query, start=1):
        rows.append({
            "row_id": f"ad_hoc_query_{i}",
            "theorem": "",
            "source_file": "",
            "source_hinge": q,
            "non_timeout_candidate_family": "",
        })
    if not rows:
        raise SystemExit("no rows supplied via --source-queue or --query")
    obj = build(
        rows,
        args.endpoint,
        args.limit,
        Path(args.out) if args.out else None,
        Path(args.markdown) if args.markdown else None,
        Path(args.fixture) if args.fixture else None,
        Path(args.mathlib_root) if args.mathlib_root else None,
        args.retries,
        args.retry_sleep,
        args.request_sleep,
    )
    print(json.dumps({
        "out": args.out,
        "markdown": args.markdown,
        "row_count": obj["row_count"],
        "usable_candidate_total": obj["usable_candidate_total"],
        "exact_target_excluded_total": obj["exact_target_excluded_total"],
        "post_target_forbidden_total": obj["post_target_forbidden_total"],
        "same_module_before_target_total": obj["same_module_before_target_total"],
        "same_module_order_check_total": obj["same_module_order_check_total"],
        "status": obj["status"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
