#!/usr/bin/env python3
"""Build a conservative repair-family registry from canary event streams.

This is a read model for Residual Compiler scale discipline. It does not run Lean and it
does not award proof credit. It groups repair-canary events by family and marks
whether the evidence is still a one-row seed, a candidate family, or a validated
family under explicit promotion rules.
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from leanmill_heldout_receipt_gate import validate_receipt

DEFAULT_DISCOVER_ROOTS = ["/tmp/rung1"]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({"event": "malformed_jsonl", "path": str(path), "line_tail": line[-300:]})
    return rows


def _event_files(root: Path, name: str) -> list[Path]:
    if root.is_file() and root.name == name:
        return [root]
    if not root.exists():
        return []
    return sorted(root.glob(f"**/events/{name}"))


def _decision_files(root: Path) -> list[Path]:
    if root.is_file() and root.name.endswith(".json") and "decision" in root.name:
        return [root]
    if not root.exists() or root.is_file():
        return []
    return sorted(root.glob("**/*decision*.json"))


def _heldout_receipt_files(root: Path) -> list[Path]:
    if root.is_file() and "heldout_receipt" in root.name and root.suffix == ".json":
        return [root]
    if not root.exists() or root.is_file():
        return []
    return sorted(root.glob("**/*heldout_receipt*.json"))


def _discover_event_roots(discover_roots: list[str]) -> list[Path]:
    """Find repair-canary roots by looking for persisted event streams."""
    roots: set[Path] = set()
    for root_s in discover_roots:
        root = Path(root_s)
        if not root.exists():
            continue
        if root.is_file():
            if root.name in {"closed.jsonl", "negative_controls.jsonl"}:
                roots.add(root.parent.parent)
            continue
        for path in root.glob("**/events/closed.jsonl"):
            roots.add(path.parent.parent)
        for path in root.glob("**/events/negative_controls.jsonl"):
            roots.add(path.parent.parent)
        for path in root.glob("**/*decision*.json"):
            roots.add(path)
        for path in root.glob("**/*heldout_receipt*.json"):
            roots.add(path)
    return sorted(roots, key=lambda p: str(p))


def _input_roots(args: argparse.Namespace) -> tuple[list[Path], dict[str, Any]]:
    explicit = [Path(p) for p in (args.root or [])]
    discover_roots = list(DEFAULT_DISCOVER_ROOTS if args.discover_root is None else args.discover_root)
    discovered = _discover_event_roots(discover_roots)
    roots: list[Path] = []
    seen: set[str] = set()
    for root in [*explicit, *discovered]:
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        roots.append(root)
    return roots, {
        "explicit_roots": [str(p) for p in explicit],
        "discover_roots": discover_roots,
        "discovered_roots": [str(p) for p in discovered],
    }


def _new_family() -> dict[str, Any]:
    return {
        "family": "",
        "rows_attempted": set(),
        "ratified_rows": set(),
        "ratified_proof_closure": 0,
        "exact_gap": 0,
        "valid_falsifier": 0,
        "exact_gap_rows": set(),
        "valid_falsifier_rows": set(),
        "seed_hold": 0,
        "heldout_attempt_rows": set(),
        "heldout_success_rows": set(),
        "hold_reasons": [],
        "superseded_by": "",
        "superseded_reason": "",
        "cycle_s": [],
        "seen_at": [],
        "negative_controls_expected_fail": 0,
        "negative_controls_unexpected_pass": 0,
        "false_ratifications": 0,
        "source_credit_eligible_ratifications": 0,
        "clean_solver_credit_eligible_ratifications": 0,
        "persisted": [],
        "event_roots": set(),
    }


def _status(fam: dict[str, Any]) -> tuple[str, str]:
    useful = (
        int(fam["ratified_proof_closure"])
        + int(fam["exact_gap"])
        + int(fam["valid_falsifier"])
    )
    unique_success_rows = len(fam["ratified_rows"])
    unique_attempt_rows = len(fam["rows_attempted"])
    neg_ok = int(fam["negative_controls_expected_fail"])
    neg_bad = int(fam["negative_controls_unexpected_pass"])
    false_rat = int(fam["false_ratifications"])
    seed_hold = int(fam["seed_hold"])
    heldout_successes = len(fam["heldout_success_rows"])
    if str(fam.get("superseded_by") or ""):
        return "superseded_family", "legacy family label superseded by a governed family with cleaner controls"
    if heldout_successes >= 1 and useful >= 2 and unique_success_rows >= 2 and neg_ok >= 1 and neg_bad == 0 and false_rat == 0:
        return "validated_family", "heldout independence receipt passed with guarded useful outcomes"
    if useful >= 3 and unique_attempt_rows >= 5 and unique_success_rows >= 2 and neg_ok >= 1 and neg_bad == 0 and false_rat == 0:
        return (
            "validated_family_requires_true_holdout_check",
            "count threshold met, but this registry cannot prove heldout independence from event streams alone",
        )
    if useful >= 2 and unique_success_rows >= 2 and neg_ok >= 1 and neg_bad == 0 and false_rat == 0:
        return "candidate_family", "multiple sibling rows succeeded with guarded negative controls"
    if seed_hold and neg_bad == 0 and false_rat == 0:
        return "seed_hold", "sibling or heldout sourcing was tested and no promotable row is currently available"
    if useful >= 1 and neg_bad == 0 and false_rat == 0:
        return "seed_only", "at least one governed repair outcome, but not enough sibling evidence"
    if neg_bad > 0 or false_rat > 0:
        return "invalid_or_regression", "negative control or false-ratification guard failed"
    return "inventory_only", "no governed useful outcome yet"


def build_registry(args: argparse.Namespace) -> dict[str, Any]:
    roots, discovery = _input_roots(args)
    families: dict[str, dict[str, Any]] = defaultdict(_new_family)
    closed_events = 0
    negative_events = 0
    decision_events = 0
    heldout_receipt_events = 0
    duplicate_closed_events = 0
    seen_closed_events: set[tuple[str, str, str, str]] = set()
    seen_decision_rows: set[tuple[str, str, str]] = set()
    seen_heldout_receipts: set[str] = set()
    for root in roots:
        for path in _event_files(root, "closed.jsonl"):
            for rec in _read_jsonl(path):
                family = str(rec.get("repair_family") or rec.get("lane") or "unknown")
                row = str(rec.get("row_id") or "")
                proof_key = str(rec.get("event_id") or rec.get("proof_replay_hash") or rec.get("persisted") or "")
                if not proof_key:
                    for cand in rec.get("ratified_candidates") or []:
                        if cand.get("persisted"):
                            proof_key = str(cand.get("persisted"))
                            break
                closed_key = (family, row, str(rec.get("event") or ""), proof_key or str(path))
                if closed_key in seen_closed_events:
                    duplicate_closed_events += 1
                    continue
                seen_closed_events.add(closed_key)
                closed_events += 1
                fam = families[family]
                fam["family"] = family
                if row:
                    fam["rows_attempted"].add(row)
                    fam["ratified_rows"].add(row)
                if rec.get("event") == "ratified_closure":
                    fam["ratified_proof_closure"] += 1
                if rec.get("cycle_s") is not None:
                    fam["cycle_s"].append(float(rec.get("cycle_s") or 0))
                if rec.get("created_at"):
                    fam["seen_at"].append(str(rec.get("created_at")))
                fam["source_credit_eligible_ratifications"] += int(bool(rec.get("source_credit_eligible")))
                fam["clean_solver_credit_eligible_ratifications"] += int(bool(rec.get("clean_solver_credit_eligible")))
                fam["event_roots"].add(str(root))
                for cand in rec.get("ratified_candidates") or []:
                    persisted = cand.get("persisted")
                    if persisted:
                        fam["persisted"].append(str(persisted))
        for path in _event_files(root, "negative_controls.jsonl"):
            for rec in _read_jsonl(path):
                negative_events += 1
                family = str(rec.get("repair_family") or rec.get("lane") or "unknown")
                fam = families[family]
                fam["family"] = family
                row = str(rec.get("row_id") or "")
                if row:
                    fam["rows_attempted"].add(row)
                if rec.get("event") == "negative_control_unexpected_pass":
                    fam["negative_controls_unexpected_pass"] += 1
                else:
                    fam["negative_controls_expected_fail"] += 1
                if rec.get("cycle_s") is not None:
                    fam["cycle_s"].append(float(rec.get("cycle_s") or 0))
                if rec.get("created_at"):
                    fam["seen_at"].append(str(rec.get("created_at")))
                fam["event_roots"].add(str(root))
        for path in _decision_files(root):
            obj = _read_jsonl(path) if path.suffix == ".jsonl" else []
            if path.suffix == ".json":
                try:
                    raw = json.loads(path.read_text(errors="ignore"))
                    obj = list(raw.get("decisions") or [])
                except json.JSONDecodeError:
                    obj = []
            for rec in obj:
                decision = str(rec.get("decision") or "")
                if decision not in {
                    "exact_gap_candidate",
                    "valid_falsifier_candidate",
                    "seed_family_hold",
                    "family_superseded",
                }:
                    continue
                family = str(rec.get("repair_family") or rec.get("lane") or "unknown")
                row = str(rec.get("row_id") or "")
                key = (family, row, decision)
                if key in seen_decision_rows:
                    continue
                seen_decision_rows.add(key)
                decision_events += 1
                fam = families[family]
                fam["family"] = family
                if row:
                    fam["rows_attempted"].add(row)
                if rec.get("created_at"):
                    fam["seen_at"].append(str(rec.get("created_at")))
                if decision == "exact_gap_candidate":
                    fam["exact_gap_rows"].add(row or str(path))
                elif decision == "valid_falsifier_candidate":
                    fam["valid_falsifier_rows"].add(row or str(path))
                elif decision == "seed_family_hold":
                    fam["seed_hold"] += 1
                    reason = str(rec.get("reason") or rec.get("next_lever") or "seed hold")
                    fam["hold_reasons"].append(reason)
                else:
                    fam["superseded_by"] = str(rec.get("superseded_by") or "")
                    fam["superseded_reason"] = str(rec.get("reason") or "")
                fam["event_roots"].add(str(root))
        for path in _heldout_receipt_files(root):
            receipt_key = str(path.resolve())
            if receipt_key in seen_heldout_receipts:
                continue
            seen_heldout_receipts.add(receipt_key)
            try:
                rec = json.loads(path.read_text(errors="ignore"))
            except json.JSONDecodeError:
                continue
            family = str(rec.get("family") or "")
            row = str(rec.get("heldout_row") or "")
            if not family or not row:
                continue
            heldout_receipt_events += 1
            fam = families[family]
            fam["family"] = family
            fam["rows_attempted"].add(row)
            fam["heldout_attempt_rows"].add(row)
            if not validate_receipt(rec):
                fam["heldout_success_rows"].add(row)
                if rec.get("created_at"):
                    fam["seen_at"].append(str(rec.get("created_at")))
            fam["event_roots"].add(str(path))

    family_rows: list[dict[str, Any]] = []
    for family, fam in families.items():
        fam["exact_gap"] = len(fam["exact_gap_rows"])
        fam["valid_falsifier"] = len(fam["valid_falsifier_rows"])
        status, reason = _status(fam)
        neg_total = int(fam["negative_controls_expected_fail"]) + int(fam["negative_controls_unexpected_pass"])
        useful = int(fam["ratified_proof_closure"]) + int(fam["exact_gap"]) + int(fam["valid_falsifier"])
        unique_attempted = len(fam["rows_attempted"])
        unique_ratified = len(fam["ratified_rows"])
        cycle_s = [float(x) for x in fam["cycle_s"] if float(x) >= 0]
        next_required = "none"
        if status == "seed_only":
            next_required = "sibling_or_heldout_useful_outcome_with_matched_negative_control"
        elif status == "seed_hold":
            next_required = "new_source_tranche_with_distinct_sibling_before_retry"
        elif status == "candidate_family":
            next_required = "heldout_attempts_and_validated_family_receipt"
        elif status == "inventory_only":
            next_required = "first_useful_outcome_or_retirement_decision"
        elif status == "superseded_family":
            next_required = "use_superseding_family"
        row = {
            "family": family,
            "status": status,
            "status_reason": reason,
            "rows_attempted": sorted(fam["rows_attempted"]),
            "unique_rows_attempted": unique_attempted,
            "ratified_rows": sorted(fam["ratified_rows"]),
            "unique_ratified_rows": unique_ratified,
            "ratified_proof_closure": fam["ratified_proof_closure"],
            "exact_gap": fam["exact_gap"],
            "valid_falsifier": fam["valid_falsifier"],
            "useful_outcomes": useful,
            "attempted_siblings": max(0, unique_attempted - 1),
            "heldout_attempts": len(fam["heldout_attempt_rows"]),
            "heldout_successes": len(fam["heldout_success_rows"]),
            "heldout_rows": sorted(fam["heldout_success_rows"]),
            "median_drain_time_s": round(statistics.median(cycle_s), 3) if cycle_s else None,
            "negative_control_pass_rate": (
                round(float(fam["negative_controls_unexpected_pass"]) / float(neg_total), 6)
                if neg_total else 0.0
            ),
            "last_seen_at": max(fam["seen_at"]) if fam["seen_at"] else "",
            "next_required_evidence": next_required,
            "seed_hold": fam["seed_hold"],
            "hold_reasons": sorted(set(fam["hold_reasons"])),
            "superseded_by": fam["superseded_by"],
            "superseded_reason": fam["superseded_reason"],
            "negative_controls_expected_fail": fam["negative_controls_expected_fail"],
            "negative_controls_unexpected_pass": fam["negative_controls_unexpected_pass"],
            "false_ratifications": fam["false_ratifications"],
            "source_credit_eligible_ratifications": fam["source_credit_eligible_ratifications"],
            "clean_solver_credit_eligible_ratifications": fam["clean_solver_credit_eligible_ratifications"],
            "persisted": sorted(set(fam["persisted"])),
            "event_roots": sorted(fam["event_roots"]),
        }
        family_rows.append(row)
    family_rows.sort(
        key=lambda r: (
            {"validated_family": 0, "validated_family_requires_true_holdout_check": 1, "candidate_family": 2, "seed_only": 3}.get(str(r["status"]), 9),
            -int(r["ratified_proof_closure"]),
            str(r["family"]),
        )
    )
    status_counts: dict[str, int] = {}
    for row in family_rows:
        key = str(row["status"])
        status_counts[key] = status_counts.get(key, 0) + 1
    payload = {
        "schema": "leansearch-repair-family-registry-v1",
        "roots": [str(p) for p in roots],
        "discovery": discovery,
        "closed_events": closed_events,
        "duplicate_closed_events_ignored": duplicate_closed_events,
        "negative_control_events": negative_events,
        "decision_events": decision_events,
        "heldout_receipt_events": heldout_receipt_events,
        "family_count": len(family_rows),
        "status_counts": status_counts,
        "promotion_rules": {
            "seed_only": ">=1 governed useful outcome and no failed controls",
            "candidate_family": ">=2 useful outcomes across >=2 rows, >=1 expected-failing negative control, 0 unexpected negative passes, 0 false ratifications",
            "seed_hold": "sibling/heldout sourcing was checked and no promotable row is currently available",
            "validated_family_requires_true_holdout_check": ">=3 useful outcomes across >=2 rows and >=5 attempted rows, but event streams do not prove heldout independence",
            "validated_family": "candidate-family evidence plus >=1 passing heldout-independence receipt",
        },
        "families": family_rows,
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        ev = root / "events"
        ev.mkdir()
        (ev / "closed.jsonl").write_text(
            json.dumps({
                "event": "ratified_closure",
                "repair_family": "fam",
                "row_id": "r1",
                "source_credit_eligible": False,
                "ratified_candidates": [{"persisted": "/tmp/p1.lean"}],
            }) + "\n"
            + json.dumps({
                "event": "ratified_closure",
                "repair_family": "fam",
                "row_id": "r2",
                "source_credit_eligible": False,
                "ratified_candidates": [{"persisted": "/tmp/p2.lean"}],
            }) + "\n"
        )
        (ev / "negative_controls.jsonl").write_text(
            json.dumps({
                "event": "negative_control_expected_fail",
                "repair_family": "fam",
                "row_id": "r1",
            }) + "\n"
        )
        (root / "residual_decisions.json").write_text(json.dumps({
            "decisions": [{
                "decision": "exact_gap_candidate",
                "repair_family": "gap_fam",
                "row_id": "g1",
            }, {
                "decision": "seed_family_hold",
                "repair_family": "hold_fam",
                "row_id": "h1",
                "reason": "no sibling row in current corpus",
            }, {
                "decision": "family_superseded",
                "repair_family": "old_fam",
                "superseded_by": "new_fam",
                "reason": "legacy label lacks current controls",
            }]
        }) + "\n")
        report = root / "fam_heldout_governance_report.json"
        report.write_text(json.dumps({
            "event_type": "governance_ratified",
            "family": "fam",
            "heldout_row": "r3",
            "proof_replay_hash": "abc123",
        }) + "\n")
        (root / "fam_heldout_receipt.json").write_text(json.dumps({
            "schema": "leanmill-heldout-receipt-v1",
            "family": "fam",
            "heldout_row": "r3",
            "template_design_rows": ["r1", "r2"],
            "expected_outcome": "closure",
            "evidence": {
                "not_same_row": True,
                "not_same_target_alias": True,
                "not_same_source_file": True,
                "not_used_in_template_design": True,
                "matched_negative_control_failed": True,
                "governance_ratified": True,
            },
            "artifacts": {
                "proof_replay_hash": "abc123",
                "governance_report": str(report),
            },
            "credit": {
                "source_credit_eligible": False,
                "clean_solver_credit_eligible": False,
                "repair_canary_credit_eligible": True,
            },
            "produced_by_worker_class": "governance",
            "produced_by_worker_id": "leanmill-governance",
        }) + "\n")
        obj = build_registry(argparse.Namespace(root=[str(root)], discover_root=[], out=None))
        assert obj["family_count"] == 4, obj
        by_family = {row["family"]: row for row in obj["families"]}
        assert by_family["fam"]["status"] == "validated_family", obj
        assert by_family["fam"]["heldout_successes"] == 1, obj
        assert by_family["gap_fam"]["exact_gap"] == 1, obj
        assert by_family["hold_fam"]["status"] == "seed_hold", obj
        assert by_family["old_fam"]["status"] == "superseded_family", obj
        obj = build_registry(argparse.Namespace(root=[], discover_root=[str(root)], out=None))
        assert str(root) in obj["roots"], obj
        assert str(root / "residual_decisions.json") in obj["roots"], obj
        by_family = {row["family"]: row for row in obj["families"]}
        assert by_family["fam"]["status"] == "validated_family", obj
        assert by_family["gap_fam"]["exact_gap"] == 1, obj
        assert by_family["hold_fam"]["status"] == "seed_hold", obj
        assert by_family["old_fam"]["status"] == "superseded_family", obj
    print("leansearch_repair_family_registry self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", action="append")
    ap.add_argument("--discover-root", action="append", default=None)
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if not args.root and not args.discover_root:
        raise SystemExit("--root or --discover-root is required unless --self-test is used")
    print(json.dumps(build_registry(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
