#!/usr/bin/env python3
"""Build a verifier-feedback repair trajectory dataset for Path A.

This is the SOTA-shaped replacement for whole-row nearest-neighbor
routing. The row unit is an attempted repair trajectory:

  failed attempt -> Lean/gate feedback -> diagnosis -> repair class
  -> next action/outcome under the authoritative gate.

It is machine-safe: no Lean, no Codex, no network. It can consume the
older APRIL-style backfill ledger and, when present, four-arm trace
directories with raw model outputs and govern verdicts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_APRIL = "/tmp/rung1/april_trace_ledger.jsonl"
DEFAULT_OUT = "/tmp/rung1/lean_repair_trajectory_dataset.jsonl"
DEFAULT_SUMMARY = "/tmp/rung1/lean_repair_trajectory_summary.json"

ERROR_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("unknown_identifier", re.compile(r"unknown (?:identifier|constant)", re.I)),
    ("unknown_tactic", re.compile(r"unknown tactic", re.I)),
    ("type_mismatch", re.compile(r"type mismatch|application type mismatch", re.I)),
    ("unsolved_goals", re.compile(r"unsolved goals|goals remain", re.I)),
    ("timeout", re.compile(r"\btimeout\b|timed out", re.I)),
    ("sorry_or_axiom", re.compile(r"sorryAx|declaration uses 'sorry'|axiom", re.I)),
    ("kernel_reject", re.compile(r"kernel|elaboration|failed to synthesize", re.I)),
]

TACTIC_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("simp_family", re.compile(r"\b(simp|simp_all|rw|rewrite)\b")),
    ("automation_family", re.compile(r"\b(aesop|hammer|duper|auto|exact\?|apply\?)\b")),
    ("arithmetic_family", re.compile(r"\b(linarith|nlinarith|omega|ring|norm_num)\b")),
    ("structure_family", re.compile(r"\b(refine|constructor|cases|induction|intro|have)\b")),
    ("exact_apply_family", re.compile(r"\b(exact|apply)\b")),
]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(errors="ignore").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _sha(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _classify_error(text: str | None, verdict: str | None = None,
                    reason: str | None = None) -> str:
    hay = "\n".join(x for x in (text or "", verdict or "", reason or "") if x)
    if not hay.strip():
        return "no_feedback"
    for name, pat in ERROR_PATTERNS:
        if pat.search(hay):
            return name
    if verdict and verdict not in {"closure", "open"}:
        return f"gate_{verdict}"
    return "other_error"


def _classify_repair(text: str | None, diagnosis: str | None = None,
                     next_lever: str | None = None) -> str:
    hay = "\n".join(x for x in (text or "", diagnosis or "", next_lever or "") if x)
    lo = hay.lower()
    if "closed_clean" in lo or "ratify_closure" in lo:
        return "ratify_closure"
    if "exact" in lo and "gap" in lo:
        return "produce_exact_gap"
    if "missing" in lo or "prove_missing_lemma" in lo:
        return "prove_missing_lemma"
    if "budget" in lo or "search_exhausted" in lo or "timeout" in lo:
        return "increase_budget_or_decompose"
    if "composition" in lo or "wrong_proof" in lo:
        return "repair_composition"
    for name, pat in TACTIC_PATTERNS:
        if pat.search(hay):
            return name
    return "unknown_repair"


def _action_family(text: str | None) -> str:
    hay = text or ""
    for name, pat in TACTIC_PATTERNS:
        if pat.search(hay):
            return name
    return "unknown_action"


def _record_from_april(rec: dict[str, Any]) -> dict[str, Any]:
    err_text = rec.get("lean_error") or rec.get("proof_state_at_failure")
    diagnosis = rec.get("diagnosis")
    next_lever = rec.get("next_lever")
    outcome = rec.get("outcome")
    governed_solved = bool(rec.get("governed_solved"))
    visible = {
        "target": rec.get("target"),
        "source_module": rec.get("source_module"),
        "arm": rec.get("arm"),
        "gold_n_steps": rec.get("gold_n_steps"),
        "goal_excerpt": rec.get("goal_excerpt"),
        "failed_tactic_family": _action_family(rec.get("failed_tactic")),
        "error_class": _classify_error(err_text, rec.get("outcome"),
                                       rec.get("governance_residual_class")),
        "diagnosis": diagnosis,
        "repair_class": _classify_repair(rec.get("repair_attempt"),
                                         diagnosis, next_lever),
        "governance_residual_class": rec.get("governance_residual_class"),
    }
    hidden = {
        "outcome": outcome,
        "governed_solved": governed_solved,
        "label_closure_or_exact_gap": int(rec.get("label_closure_or_exact_gap") or 0),
        "cost_secs": rec.get("cost_secs"),
        "next_lever": next_lever,
    }
    return {
        "schema": "path-a-repair-trajectory-v1",
        "source": "april_backfill",
        "trace_id": rec.get("trace_id") or _sha(rec)[:16],
        "capture_status": rec.get("capture_status") or "unknown",
        "visible": visible,
        "hidden": hidden,
        "visible_hash": _sha(visible),
        "hidden_hash": _sha(hidden),
    }


def _read(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")
    except OSError:
        return ""


def _round_records(trace_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not trace_root.exists():
        return rows
    for raw in sorted(trace_root.glob("*/*/round_*.raw_model_output.txt")):
        arm_dir = raw.parent
        arm = arm_dir.name
        target = arm_dir.parent.name
        round_id = raw.stem.replace(".raw_model_output", "")
        govern = arm_dir / f"{round_id}.govern.json"
        call = arm_dir / f"{round_id}.call.json"
        proof_files = sorted(arm_dir.glob(f"{round_id}.*.lean"))
        raw_text = _read(raw)
        proof_text = "\n".join(_read(p) for p in proof_files)
        gov = {}
        if govern.exists():
            try:
                gov = json.loads(govern.read_text(errors="ignore"))
            except json.JSONDecodeError:
                gov = {"verdict": "unreadable_govern"}
        call_j = {}
        if call.exists():
            try:
                call_j = json.loads(call.read_text(errors="ignore"))
            except json.JSONDecodeError:
                call_j = {}
        verdict = str(gov.get("verdict") or call_j.get("codex_status") or "open")
        reason = str(gov.get("reason") or "")
        visible = {
            "target": target,
            "arm": arm,
            "round": round_id,
            "failed_tactic_family": _action_family(proof_text or raw_text),
            "error_class": _classify_error(raw_text, verdict, reason),
            "diagnosis": reason or verdict,
            "repair_class": _classify_repair(proof_text or raw_text, reason, None),
            "raw_output_chars": len(raw_text),
            "proof_chars": len(proof_text),
        }
        hidden = {
            "verdict": verdict,
            "ratified": int(verdict == "closure" or bool(gov.get("ratified"))),
            "reason": reason,
            "elapsed_s": call_j.get("elapsed_s"),
            "trace_dir": str(arm_dir),
        }
        rows.append({
            "schema": "path-a-repair-trajectory-v1",
            "source": "four_arm_trace_dir",
            "trace_id": f"{target}::{arm}::{round_id}",
            "capture_status": "round_trace",
            "visible": visible,
            "hidden": hidden,
            "visible_hash": _sha(visible),
            "hidden_hash": _sha(hidden),
        })
    return rows


def build(april_ledger: Path | None, trace_roots: list[Path],
          out: Path, summary: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    if april_ledger:
        records.extend(_record_from_april(r) for r in _load_jsonl(april_ledger))
    for root in trace_roots:
        records.extend(_round_records(root))

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records))

    by_source = Counter(r["source"] for r in records)
    by_error = Counter(r["visible"].get("error_class") for r in records)
    by_repair = Counter(r["visible"].get("repair_class") for r in records)
    closure_by_repair: dict[str, Counter[str]] = defaultdict(Counter)
    for r in records:
        repair = str(r["visible"].get("repair_class"))
        hidden = r.get("hidden") or {}
        positive = bool(hidden.get("label_closure_or_exact_gap") or hidden.get("ratified"))
        closure_by_repair[repair]["positive" if positive else "negative"] += 1
    summary_obj = {
        "schema": "path-a-repair-trajectory-summary-v1",
        "out": str(out),
        "n": len(records),
        "by_source": dict(by_source),
        "error_class_counts": dict(by_error),
        "repair_class_counts": dict(by_repair),
        "repair_class_outcomes": {k: dict(v) for k, v in closure_by_repair.items()},
        "sota_alignment": [
            "APRIL-style failed proof plus compiler feedback rows",
            "OProver-style failed attempt plus verified repair memory",
            "APOLLO-style modular failure isolation before LLM retry",
            "Path B gate remains the only closure authority",
        ],
    }
    summary.write_text(json.dumps(summary_obj, indent=1, sort_keys=True) + "\n")
    return summary_obj


def self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        april = root / "april.jsonl"
        april.write_text(json.dumps({
            "trace_id": "r1",
            "target": "T",
            "source_module": "M.lean",
            "arm": "A",
            "goal_excerpt": "x : Nat\n⊢ x = x",
            "failed_tactic": "simp",
            "lean_error": "unsolved goals",
            "diagnosis": "composition_wrong_proof",
            "repair_attempt": "rw [Nat.add_comm]; simp",
            "outcome": "no_closure",
            "governed_solved": False,
            "governance_residual_class": "theorem_or_pde_gap",
            "next_lever": "prove_missing_lemma",
        }) + "\n")
        trace = root / "traces" / "T2" / "A"
        trace.mkdir(parents=True)
        (trace / "round_01.raw_model_output.txt").write_text("error: type mismatch")
        (trace / "round_01.govern.json").write_text(json.dumps({
            "verdict": "unverified",
            "reason": "type mismatch",
        }))
        (trace / "round_01.call.json").write_text(json.dumps({"elapsed_s": 1.2}))
        out = root / "out.jsonl"
        summ = root / "summary.json"
        s = build(april, [root / "traces"], out, summ)
        assert s["n"] == 2
        rows = _load_jsonl(out)
        assert rows[0]["visible"]["repair_class"] == "prove_missing_lemma"
        assert rows[1]["visible"]["error_class"] == "type_mismatch"
    print("lean_repair_trajectory_dataset self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--april-ledger", default=DEFAULT_APRIL)
    ap.add_argument("--trace-root", action="append", default=[])
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--summary", default=DEFAULT_SUMMARY)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    april = Path(args.april_ledger) if args.april_ledger else None
    roots = [Path(p) for p in args.trace_root]
    result = build(april, roots, Path(args.out), Path(args.summary))
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
