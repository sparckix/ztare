#!/usr/bin/env python3
"""Optional LLM proposer for LeanMill repair-canary tactic bodies.

This station is intentionally proposal-only. It reads source/residual packets,
asks a fast model for bounded Lean tactic bodies, and emits a canary packet that
`leansearch_repair_canary_drain.py` can execute. The model never scores itself:
compile, governance, negative controls, and credit assignment remain downstream.

Status: off by default / experimental. First 2026-05-20 probe produced one
useful exact-gap candidate and duplicate weak repair attempts, so the mainline
Mill should prefer deterministic qualification plus human-authored repairs
unless a future pre-registered test shows this station improves canary yield.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import textwrap
import time
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[5]
DEFAULT_PACKET = "analytics/public/leanmill/dashboard_data/residual_family_canary_packets.json"
DEFAULT_CORPUS = "/tmp/rung1/mcb_corpus_v2.json"
DEFAULT_OUT = "analytics/public/leanmill/dashboard_data/llm_template_proposals.json"
DEFAULT_CANARY_OUT = "analytics/public/leanmill/dashboard_data/llm_template_canary_packets.json"
DEFAULT_PROMPT_OUT = "/tmp/rung1/leanmill_llm_template_prompt.txt"
DEFAULT_RAW_OUT = "/tmp/rung1/leanmill_llm_template_raw.txt"


def _read_json(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(errors="ignore"))


def _rows(obj: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        return obj
    return list(obj.get("rows") or obj.get("corpus") or obj.get("targets") or [])


def _row_by_id(corpus: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in _rows(corpus):
        rid = str(row.get("row_id") or row.get("id") or "")
        if rid:
            out[rid] = row
    return out


def _candidate_meta(static_filter: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for row in _rows(static_filter):
        rid = str(row.get("row_id") or row.get("id") or "")
        for cand in (
            row.get("canary_ready_candidates")
            or row.get("row_context_ready_candidates")
            or row.get("target_context_ready_candidates")
            or row.get("candidates")
            or []
        ):
            name = str(cand.get("name") or "")
            if rid and name:
                out[(rid, name)] = cand
    return out


def _source_excerpt(row: dict[str, Any], radius: int = 34) -> str:
    path = row.get("sorried_file")
    if not path:
        return ""
    p = Path(str(path))
    if not p.exists():
        return ""
    lines = p.read_text(errors="ignore").splitlines()
    target = max(1, int(row.get("target_line") or 1))
    lo = max(1, target - radius)
    hi = min(len(lines), target + radius)
    return "\n".join(f"{i:04d}: {lines[i - 1]}" for i in range(lo, hi + 1))


def _tests_from_packet(packet: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    for pkt in packet.get("packets") or []:
        family = str(pkt.get("repair_family") or "")
        for t in pkt.get("tests") or []:
            tests.append({**t, "repair_family": t.get("repair_family") or family})
        if pkt.get("tests"):
            continue
        for row in pkt.get("selected_rows") or []:
            rid = str(row.get("row_id") or "")
            for name in row.get("candidate_names") or []:
                tests.append({
                    "packet_id": f"{family}:{rid}:{name}:llm_template",
                    "repair_family": family,
                    "row_id": rid,
                    "candidate_name": str(name),
                    "test_kind": "positive",
                    "expected_outcome": "closure_or_typed_residual",
                    "source_credit_eligible": False,
                    "clean_solver_credit_eligible": False,
                })
    return tests[:limit]


def _previous_result_snippet(results_root: str | None, row_id: str) -> dict[str, Any] | None:
    if not results_root:
        return None
    root = Path(results_root)
    if not root.exists():
        return None
    paths = sorted(root.glob(f"**/*{row_id}*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in paths[:4]:
        try:
            obj = json.loads(path.read_text(errors="ignore"))
        except Exception:
            continue
        results = obj.get("results") or []
        if not results:
            continue
        first = results[0]
        return {
            "artifact": str(path),
            "candidate": first.get("candidate"),
            "action_family": first.get("action_family"),
            "error_class": first.get("error_class"),
            "closed": bool(first.get("closed")),
            "stdout_tail": str(first.get("stdout_tail") or "")[-1200:],
            "repl_trace_tail": str(first.get("repl_step_trace") or "")[-1200:],
        }
    return None


def _items(args: argparse.Namespace) -> list[dict[str, Any]]:
    packet = _read_json(args.packet)
    corpus = _read_json(args.corpus)
    static = _read_json(args.static_filter)
    rows = _row_by_id(corpus)
    metas = _candidate_meta(static)
    items: list[dict[str, Any]] = []
    for test in _tests_from_packet(packet, args.limit):
        rid = str(test.get("row_id") or "")
        cname = str(test.get("candidate_name") or "")
        row = rows.get(rid, {})
        meta = metas.get((rid, cname), {})
        items.append({
            "packet_id": test.get("packet_id"),
            "repair_family": test.get("repair_family"),
            "row_id": rid,
            "candidate_name": cname,
            "test_kind": test.get("test_kind", "positive"),
            "expected_outcome": test.get("expected_outcome"),
            "theorem": row.get("theorem") or row.get("statement") or row.get("goal"),
            "goal": row.get("goal"),
            "source_excerpt": _source_excerpt(row, args.source_radius),
            "candidate_type": meta.get("type") or meta.get("signature"),
            "candidate_templates": meta.get("candidate_action_templates") or [],
            "previous_result": _previous_result_snippet(args.previous_results_root, rid),
        })
    return items


def _prompt(items: list[dict[str, Any]]) -> str:
    payload = json.dumps(items, indent=2, ensure_ascii=False)[:90000]
    return textwrap.dedent(f"""
    You propose Lean canary specs and tactic bodies for LeanMill repair canaries.

    Your output is only a proposal. Lean compilation and Path-B governance will
    judge it. Do not claim success. Do not use `sorry`, `admit`, `axiom`,
    `constant`, `opaque`, new theorem declarations, imports, or namespace
    changes. Emit bodies that can replace the target `sorry` after `:= by`.

    Prefer small, typed repair attempts over broad search tactics. You may use
    a candidate theorem named in the packet. If the candidate is clearly the
    wrong shape, propose the smallest diagnostic body that will expose the
    missing adapter rather than pretending it should close.

    Return STRICT JSON:
    {{
      "schema": "leanmill-llm-template-response-v1",
      "proposals": [
        {{
          "packet_id": "...",
          "row_id": "...",
          "repair_family": "...",
          "candidate_name": "...",
          "proposal_id": "short_ascii_id",
          "proposed_action": "apply|exact|rw_fwd|rw_rev|simp|convert|constructor|diagnostic",
          "why_relevant": "...",
          "required_assumptions": ["..."],
          "expected_positive_delta": "closes target|reduces to side goal|exposes exact gap|typed residual",
          "lean_body": "multi-line Lean tactic body replacing the target sorry",
          "expected_mechanism": "...",
          "expected_failure_if_not_close": "type_mismatch|missing_instance|unsolved_goals|unknown_identifier|internal_exception|other",
          "negative_control_body": null,
          "negative_control": {{
            "mutation": "remove assumption|reverse iff|wrong argument|wrong interval|wrong carrier|none",
            "expected_result": "must_fail|not_available"
          }},
          "credit_type": "external_source|repair_canary|synthetic_control|practice_only",
          "confidence": 0.0
        }}
      ]
    }}

    Packet:
    {payload}
    """).strip()


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    decoder = json.JSONDecoder()
    for idx, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[idx:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    raise ValueError("no JSON object found")


_FORBIDDEN_BODY_RE = re.compile(r"\b(sorry|admit|axiom|constant|opaque|import|theorem|lemma|def)\b")
_ACTIONS = {"apply", "exact", "rw_fwd", "rw_rev", "simp", "convert", "constructor", "diagnostic"}
_CREDIT_TYPES = {"external_source", "repair_canary", "synthetic_control", "practice_only"}


def _clean_body(body: str) -> str:
    body = str(body or "").replace("\r\n", "\n").strip()
    if body == "by":
        body = ""
    elif body.startswith("by\n"):
        body = body[3:].lstrip("\n")
    if len(body) > 4000:
        body = body[:4000].rstrip()
    return body


def _body_without_comments(body: str) -> str:
    lines = []
    for line in body.splitlines():
        if "--" in line:
            line = line.split("--", 1)[0]
        lines.append(line)
    return "\n".join(lines)


def _validate_proposal(p: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    for key in ["packet_id", "row_id", "repair_family", "proposal_id", "lean_body"]:
        if not str(p.get(key) or "").strip():
            errors.append(f"missing_{key}")
    action = str(p.get("proposed_action") or "")
    if action and action not in _ACTIONS:
        errors.append("illegal_proposed_action")
    credit_type = str(p.get("credit_type") or "")
    if credit_type and credit_type not in _CREDIT_TYPES:
        errors.append("illegal_credit_type")
    body = _clean_body(str(p.get("lean_body") or ""))
    if _FORBIDDEN_BODY_RE.search(_body_without_comments(body)):
        errors.append("forbidden_token_in_body")
    if not body:
        errors.append("empty_body")
    if body.count("\n") > 80:
        errors.append("body_too_long")
    return (not errors), errors


def _normalize_response(obj: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    item_by_packet = {str(x.get("packet_id")): x for x in items}
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for raw in obj.get("proposals") or []:
        if not isinstance(raw, dict):
            continue
        packet_id = str(raw.get("packet_id") or "")
        item = item_by_packet.get(packet_id, {})
        rec = {
            "packet_id": packet_id,
            "row_id": str(raw.get("row_id") or item.get("row_id") or ""),
            "repair_family": str(raw.get("repair_family") or item.get("repair_family") or ""),
            "candidate_name": str(raw.get("candidate_name") or item.get("candidate_name") or ""),
            "proposal_id": re.sub(r"[^A-Za-z0-9_]+", "_", str(raw.get("proposal_id") or "llm_template"))[:80],
            "proposed_action": str(raw.get("proposed_action") or "diagnostic"),
            "why_relevant": str(raw.get("why_relevant") or raw.get("expected_mechanism") or ""),
            "required_assumptions": list(raw.get("required_assumptions") or []),
            "expected_positive_delta": str(raw.get("expected_positive_delta") or "typed residual"),
            "lean_body": _clean_body(str(raw.get("lean_body") or "")),
            "expected_mechanism": str(raw.get("expected_mechanism") or ""),
            "expected_failure_if_not_close": str(raw.get("expected_failure_if_not_close") or ""),
            "negative_control_body": raw.get("negative_control_body"),
            "negative_control": raw.get("negative_control") or {
                "mutation": "none",
                "expected_result": "not_available",
            },
            "confidence": raw.get("confidence"),
            "source_credit_eligible": False,
            "clean_solver_credit_eligible": False,
            "credit_kind": "llm_repair_canary",
            "credit_type": str(raw.get("credit_type") or "repair_canary"),
        }
        ok, errors = _validate_proposal(rec)
        if ok:
            accepted.append(rec)
        else:
            rejected.append({**rec, "reject_reasons": errors})
    return {
        "schema": "leanmill-llm-template-proposals-v1",
        "created_at_epoch": int(time.time()),
        "proposal_count": len(accepted),
        "rejected_count": len(rejected),
        "proposals": accepted,
        "rejected": rejected,
        "science_rule": "LLM proposals are repair-canary inventory only. Value credit requires Lean execution and Path-B ratification or exact-gap/falsifier adjudication.",
    }


def _proposal_packet(proposals: dict[str, Any], static_filter: str, timeout: int, backend: str) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for p in proposals.get("proposals") or []:
        grouped.setdefault(str(p.get("repair_family") or "llm_template"), []).append(p)
    packets = []
    for family, props in grouped.items():
        tests = []
        for p in props:
            body = str(p.get("lean_body") or "").strip()
            is_gap_candidate = body.startswith("fail ") and p.get("expected_positive_delta") == "exposes exact gap"
            test = {
                "packet_id": f"{p['packet_id']}:{p['proposal_id']}",
                "repair_family": family,
                "row_id": p["row_id"],
                "candidate_name": p.get("candidate_name"),
                "action_family": "",
                "test_kind": "positive",
                "expected_outcome": "closure_or_typed_residual",
                "candidate_kind": "exact_gap_candidate" if is_gap_candidate else "repair_template",
                "source_credit_eligible": False,
                "clean_solver_credit_eligible": False,
                "static_filter": static_filter,
                "backend": backend,
                "timeout": timeout,
                "max_candidates": 0,
                "max_actions": 0,
                "extra_body": [f"{p['proposal_id']}::{p['lean_body']}"],
                "canary_spec": {
                    "target_id": p["row_id"],
                    "source_decl": p.get("candidate_name"),
                    "residual_family": family,
                    "proposed_action": p.get("proposed_action"),
                    "why_relevant": p.get("why_relevant"),
                    "required_assumptions": p.get("required_assumptions") or [],
                    "expected_positive_delta": p.get("expected_positive_delta"),
                    "negative_control": p.get("negative_control"),
                    "timeout_sec": timeout,
                    "credit_type": p.get("credit_type"),
                },
                "expected_mechanism": p.get("expected_mechanism"),
                "expected_failure_if_not_close": p.get("expected_failure_if_not_close"),
            }
            tests.append(test)
            ncb = p.get("negative_control_body")
            if isinstance(ncb, str) and ncb.strip():
                tests.append({
                    **test,
                    "packet_id": f"{p['packet_id']}:{p['proposal_id']}:negative",
                    "test_kind": "negative_control",
                    "expected_outcome": "must_not_close",
                "extra_body": [f"{p['proposal_id']}_negative::{_clean_body(ncb)}"],
                "canary_spec": {
                    "target_id": p["row_id"],
                    "source_decl": p.get("candidate_name"),
                    "residual_family": family,
                    "proposed_action": "diagnostic",
                    "why_relevant": "negative control supplied by LLM proposer",
                    "required_assumptions": p.get("required_assumptions") or [],
                    "expected_positive_delta": "must not close",
                    "negative_control": p.get("negative_control"),
                    "timeout_sec": timeout,
                    "credit_type": "synthetic_control",
                },
            })
        packets.append({
            "repair_family": family,
            "state": "ready_for_canary_drain" if tests else "empty",
            "tests": tests,
            "science_rule": "Generated tests are non-scoring until drained through Lean and governance.",
        })
    return {
        "schema": "leanmill-llm-template-canary-packets-v1",
        "packet_count": len(packets),
        "test_count": sum(len(p["tests"]) for p in packets),
        "packets": packets,
    }


def _call_llm(prompt: str, model: str, max_tokens: int, timeout: int, reasoning_effort: str) -> dict[str, Any]:
    sys.path.insert(0, str(REPO))
    from src.ztare.common.llm_runtime import LLMRuntime

    runtime = LLMRuntime()
    resp = runtime.call_text(
        prompt,
        model_id=model,
        max_tokens=max_tokens,
        timeout_seconds=timeout,
        request_label="leanmill_llm_template_proposer",
        config={
            "reasoning_effort": reasoning_effort,
            "response_format": {"type": "json_object"},
        } if model.startswith("gpt-5") else None,
    )
    return {
        "text": resp.text or "",
        "model_name": resp.model_name,
        "requested_model_id": resp.requested_model_id,
        "effective_model_id": resp.effective_model_id,
        "fallback_from_model_id": resp.fallback_from_model_id,
        "usage": {
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
            "thinking_tokens": resp.usage.thinking_tokens,
            "cache_read_input_tokens": resp.usage.cache_read_input_tokens,
        },
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    items = _items(args)
    prompt = _prompt(items)
    if args.prompt_out:
        Path(args.prompt_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.prompt_out).write_text(prompt + "\n")
    if args.mode == "stub":
        response_obj = {"schema": "leanmill-llm-template-response-v1", "proposals": []}
        raw_meta = {"mode": "stub", "text": json.dumps(response_obj)}
    elif args.mode == "parse-existing":
        raw_text = Path(args.raw_in).read_text(errors="ignore")
        response_obj = _extract_json_object(raw_text)
        raw_meta = {"mode": "parse-existing", "text": raw_text}
    else:
        try:
            raw_meta = _call_llm(prompt, args.model, args.max_tokens, args.timeout, args.reasoning_effort)
            response_obj = _extract_json_object(raw_meta["text"])
        except Exception as exc:
            raw_meta = {
                "mode": "llm",
                "text": "",
                "error": f"{type(exc).__name__}: {exc}",
            }
            response_obj = {"schema": "leanmill-llm-template-response-v1", "proposals": []}
    if args.raw_out:
        Path(args.raw_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.raw_out).write_text(str(raw_meta.get("text") or "") + "\n")
    proposals = _normalize_response(response_obj, items)
    proposals.update({
        "mode": args.mode,
        "model": args.model,
        "input_item_count": len(items),
        "prompt_out": args.prompt_out,
        "raw_out": args.raw_out,
        "llm_meta": {k: v for k, v in raw_meta.items() if k != "text"},
    })
    packet = _proposal_packet(proposals, args.static_filter, args.test_timeout, args.backend)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(proposals, indent=2, sort_keys=True) + "\n")
    if args.canary_out:
        Path(args.canary_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.canary_out).write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n")
    return {
        "schema": "leanmill-llm-template-proposer-run-v1",
        "mode": args.mode,
        "model": args.model,
        "input_item_count": len(items),
        "proposal_count": proposals["proposal_count"],
        "rejected_count": proposals["rejected_count"],
        "canary_test_count": packet["test_count"],
        "out": args.out,
        "canary_out": args.canary_out,
        "science_rule": proposals["science_rule"],
    }


def _self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        packet = root / "packet.json"
        corpus = root / "corpus.json"
        static = root / "static.json"
        src = root / "r.lean"
        src.write_text("theorem r : True := by\n  sorry\n")
        packet.write_text(json.dumps({"packets": [{
            "repair_family": "iff_direction_planner",
            "selected_rows": [{"row_id": "r", "candidate_names": ["A.b"]}],
        }]}))
        corpus.write_text(json.dumps({"rows": [{"row_id": "r", "theorem": "theorem r : True", "sorried_file": str(src), "target_line": 1}]}))
        static.write_text(json.dumps({"rows": [{"row_id": "r", "canary_ready_candidates": [{"name": "A.b", "type": "True"}]}]}))
        items = _items(argparse.Namespace(
            packet=str(packet),
            corpus=str(corpus),
            static_filter=str(static),
            limit=1,
            source_radius=4,
            previous_results_root=None,
        ))
        assert items and items[0]["row_id"] == "r"
        raw = {
            "schema": "leanmill-llm-template-response-v1",
            "proposals": [{
                "packet_id": items[0]["packet_id"],
                "row_id": "r",
                "repair_family": "iff_direction_planner",
                "candidate_name": "A.b",
                "proposal_id": "p1",
                "proposed_action": "exact",
                "why_relevant": "trivial self-test",
                "required_assumptions": [],
                "expected_positive_delta": "closes target",
                "lean_body": "exact True.intro",
                "expected_mechanism": "trivial smoke",
                "expected_failure_if_not_close": "other",
                "negative_control_body": None,
                "negative_control": {"mutation": "none", "expected_result": "not_available"},
                "credit_type": "repair_canary",
                "confidence": 0.5,
            }],
        }
        proposals = _normalize_response(raw, items)
        assert proposals["proposal_count"] == 1, proposals
        canary = _proposal_packet(proposals, str(static), 5, "repl_step")
        assert canary["test_count"] == 1, canary
        assert canary["packets"][0]["tests"][0]["extra_body"][0].endswith("exact True.intro")
        raw["proposals"][0]["lean_body"] = "by\n  -- theorem in a comment is allowed\n  exact True.intro"
        proposals = _normalize_response(raw, items)
        assert proposals["proposal_count"] == 1, proposals
    print("leansearch_llm_template_proposer self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--packet", default=DEFAULT_PACKET)
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--static-filter", required=False)
    ap.add_argument("--previous-results-root")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--canary-out", default=DEFAULT_CANARY_OUT)
    ap.add_argument("--prompt-out", default=DEFAULT_PROMPT_OUT)
    ap.add_argument("--raw-out", default=DEFAULT_RAW_OUT)
    ap.add_argument("--raw-in")
    ap.add_argument("--mode", choices=["stub", "llm", "parse-existing"], default="stub")
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--max-tokens", type=int, default=6000)
    ap.add_argument("--timeout", type=int, default=240)
    ap.add_argument("--reasoning-effort", choices=["low", "medium", "high", "xhigh"], default="medium")
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--source-radius", type=int, default=30)
    ap.add_argument("--backend", choices=["subprocess", "repl", "repl_step", "repl_file"], default="repl_step")
    ap.add_argument("--test-timeout", type=int, default=90)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if not args.static_filter:
        raise SystemExit("--static-filter is required unless --self-test is used")
    print(json.dumps(run(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
