#!/usr/bin/env python3
"""Validate typed LLM repair/source/decomposition proposals.

LLMs may propose work; this gate makes proposals structured enough for the
Family Spec Gate, Residual Compiler, and Governance Gate to reject or consume.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from leanmill_source_query_contract import query_identity, queries_pass_gate, source_queries_from_proposal


VALID_PROPOSAL_TYPES = {"repair_template", "source_request", "decomposition", "exact_gap", "falsifier"}
VALID_CREDIT_TYPES = {"repair_canary", "source_credit_candidate", "clean_solver_candidate", "none"}
VALID_OUTCOMES = {"closure", "exact_gap", "falsifier", "source_request", "retire", "hold"}


def _source_queries(obj: dict[str, Any]) -> list[str]:
    raw = obj.get("source_query") or obj.get("source_queries") or obj.get("queries") or []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in source_queries_from_proposal({"source_query": raw}):
        query = query_identity(item)
        if query and query not in out:
            out.append(query)
    return out


def _target_rows(obj: dict[str, Any]) -> list[str]:
    raw = obj.get("target_row_ids") or obj.get("target_rows") or []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        row_id = str(item or "").strip()
        if row_id and row_id not in out:
            out.append(row_id)
    return out


def _read(path: str) -> Any:
    p = Path(path)
    if not p.exists():
        return []
    text = p.read_text(errors="ignore")
    if p.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    obj = json.loads(text)
    if isinstance(obj, list):
        return obj
    return [obj]


def validate_one(obj: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for key in ("family", "proposal_type", "hypothesis", "credit_type", "expected_outcome"):
        if not str(obj.get(key) or ""):
            failures.append({"failure": f"missing_{key}", "proposal": obj.get("id") or obj.get("family")})
    if str(obj.get("proposal_type") or "") not in VALID_PROPOSAL_TYPES:
        failures.append({"failure": "invalid_proposal_type", "proposal_type": obj.get("proposal_type")})
    if str(obj.get("credit_type") or "") not in VALID_CREDIT_TYPES:
        failures.append({"failure": "invalid_credit_type", "credit_type": obj.get("credit_type")})
    if str(obj.get("expected_outcome") or "") not in VALID_OUTCOMES:
        failures.append({"failure": "invalid_expected_outcome", "expected_outcome": obj.get("expected_outcome")})
    ptype = str(obj.get("proposal_type") or "")
    if ptype == "repair_template":
        if not str(obj.get("positive_template") or ""):
            failures.append({"failure": "repair_template_missing_positive_template"})
        if not str(obj.get("negative_control") or ""):
            failures.append({"failure": "repair_template_missing_negative_control"})
    if ptype == "source_request":
        query_count = len(_source_queries(obj))
        if query_count < 3 or query_count > 8:
            failures.append({"failure": "source_request_requires_three_to_eight_source_queries", "query_count": query_count})
        _queries_ok, query_quality = queries_pass_gate(obj.get("source_query") or obj.get("source_queries") or obj.get("queries") or [], str(obj.get("family") or ""))
        accepted_count = sum(1 for q in query_quality if q.get("accepted"))
        if accepted_count < 3:
            failures.append({
                "failure": "source_request_requires_three_accepted_typed_queries",
                "accepted_query_count": accepted_count,
                "query_quality": query_quality[:8],
            })
        target_row_count = len(_target_rows(obj))
        if target_row_count < 1 or target_row_count > 12:
            failures.append({"failure": "source_request_requires_one_to_twelve_target_row_ids", "target_row_count": target_row_count})
    if ptype in {"exact_gap", "falsifier"} and not str(obj.get("formal_statement") or obj.get("gap_statement") or ""):
        failures.append({"failure": "gap_or_falsifier_missing_formal_statement"})
    assumptions = obj.get("required_assumptions")
    if assumptions is not None and not isinstance(assumptions, list):
        failures.append({"failure": "required_assumptions_must_be_list"})
    return failures


def build(args: argparse.Namespace) -> dict[str, Any]:
    proposals = [p for p in _read(args.proposals) if isinstance(p, dict)]
    failures: list[dict[str, Any]] = []
    for proposal in proposals:
        failures.extend(validate_one(proposal))
    payload = {
        "schema": "leanmill-llm-proposal-gate-v1",
        "proposal_count": len(proposals),
        "failure_count": len(failures),
        "failures": failures,
        "status": "pass" if not failures else "fail",
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    good = {
        "family": "fam",
        "proposal_type": "repair_template",
        "hypothesis": "typed repair",
        "positive_template": "exact h",
        "negative_control": "omit h",
        "required_assumptions": [],
        "credit_type": "repair_canary",
        "expected_outcome": "closure",
    }
    assert not validate_one(good)
    source_request = {
        "family": "fam",
        "proposal_type": "source_request",
        "hypothesis": "source request",
        "source_query": ["Filter.Tendsto.comp", "ENNReal.tsum_coe", "Summable.comp_injective"],
        "target_row_ids": ["MCB_001_example"],
        "credit_type": "none",
        "expected_outcome": "source_request",
    }
    assert not validate_one(source_request)
    nested_source_request = dict(source_request)
    nested_source_request["source_query"] = [
        {"schema": "leanmill-source-query-contract-v1", "kind": "declaration_ref", "query": {"decl_name": "Filter.Tendsto.comp"}},
        {"schema": "leanmill-source-query-contract-v1", "kind": "declaration_ref", "query": {"decl_name": "ENNReal.tsum_coe"}},
        {"schema": "leanmill-source-query-contract-v1", "kind": "declaration_ref", "query": {"decl_name": "Summable.comp_injective"}},
    ]
    assert not validate_one(nested_source_request)
    bad_source = dict(source_request)
    bad_source["source_query"] = ["only_one"]
    assert validate_one(bad_source)
    assert validate_one({"family": "fam"})
    print("leanmill_llm_proposal_gate self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--proposals")
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if not args.proposals:
        raise SystemExit("--proposals is required")
    payload = build(args)
    print(json.dumps({"status": payload["status"], "proposal_count": payload["proposal_count"], "failure_count": payload["failure_count"], "out": args.out}, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
