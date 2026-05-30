#!/usr/bin/env python3
"""Converge repair-family registry snapshots from multiple LeanMill nodes.

The repair-family registry is a control-plane artifact. A node may rebuild it
from local scratch evidence, but routing and family-spec gates should not drift
only because useful governed evidence happened on another host.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import tempfile
from pathlib import Path
from typing import Any


SCHEMA = "leansearch-repair-family-registry-v1"
RECEIPT_SCHEMA = "leanmill-registry-convergence-receipt-v1"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(errors="ignore"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _new_family(family: str) -> dict[str, Any]:
    return {
        "family": family,
        "rows_attempted": set(),
        "ratified_rows": set(),
        "exact_gap_rows": set(),
        "valid_falsifier_rows": set(),
        "heldout_rows": set(),
        "hold_reasons": set(),
        "persisted": set(),
        "event_roots": set(),
        "roots": set(),
        "last_seen_at": [],
        "median_drain_time_s": [],
        "superseded_by": set(),
        "superseded_reason": set(),
        "ratified_proof_closure": 0,
        "exact_gap": 0,
        "valid_falsifier": 0,
        "heldout_attempts": 0,
        "heldout_successes": 0,
        "seed_hold": 0,
        "negative_controls_expected_fail": 0,
        "negative_controls_unexpected_pass": 0,
        "false_ratifications": 0,
        "source_credit_eligible_ratifications": 0,
        "clean_solver_credit_eligible_ratifications": 0,
    }


def _status(fam: dict[str, Any]) -> tuple[str, str]:
    useful = _as_int(fam["ratified_proof_closure"]) + _as_int(fam["exact_gap"]) + _as_int(fam["valid_falsifier"])
    unique_success_rows = len(fam["ratified_rows"])
    unique_attempt_rows = len(fam["rows_attempted"])
    neg_ok = _as_int(fam["negative_controls_expected_fail"])
    neg_bad = _as_int(fam["negative_controls_unexpected_pass"])
    false_rat = _as_int(fam["false_ratifications"])
    seed_hold = _as_int(fam["seed_hold"])
    heldout_successes = max(_as_int(fam["heldout_successes"]), len(fam["heldout_rows"]))
    has_superseded = bool(fam["superseded_by"])

    if neg_bad > 0 or false_rat > 0:
        return "invalid_or_regression", "negative control or false-ratification guard failed in at least one source registry"
    if has_superseded and useful == 0:
        return "superseded_family", "legacy family label superseded by a governed family with cleaner controls"
    if heldout_successes >= 1 and useful >= 2 and unique_success_rows >= 2 and neg_ok >= 1:
        return "validated_family", "heldout independence receipt passed with guarded useful outcomes"
    if useful >= 3 and unique_attempt_rows >= 5 and unique_success_rows >= 2 and neg_ok >= 1:
        return (
            "validated_family_requires_true_holdout_check",
            "count threshold met, but this registry cannot prove heldout independence from event streams alone",
        )
    if useful >= 2 and unique_success_rows >= 2 and neg_ok >= 1:
        return "candidate_family", "multiple sibling rows succeeded with guarded negative controls"
    if seed_hold:
        return "seed_hold", "sibling or heldout sourcing was tested and no promotable row is currently available"
    if useful >= 1:
        return "seed_only", "at least one governed repair outcome, but not enough sibling evidence"
    return "inventory_only", "no governed useful outcome yet"


def _next_required(status: str) -> str:
    if status == "seed_only":
        return "sibling_or_heldout_useful_outcome_with_matched_negative_control"
    if status == "seed_hold":
        return "new_source_tranche_with_distinct_sibling_before_retry"
    if status == "candidate_family":
        return "heldout_attempts_and_validated_family_receipt"
    if status == "inventory_only":
        return "first_useful_outcome_or_retirement_decision"
    if status == "superseded_family":
        return "use_superseding_family"
    return "none"


def _merge_family(dst: dict[str, Any], row: dict[str, Any], *, root: str) -> None:
    dst["rows_attempted"].update(str(x) for x in _as_list(row.get("rows_attempted")) if str(x))
    dst["ratified_rows"].update(str(x) for x in _as_list(row.get("ratified_rows")) if str(x))
    dst["heldout_rows"].update(str(x) for x in _as_list(row.get("heldout_rows")) if str(x))
    dst["hold_reasons"].update(str(x) for x in _as_list(row.get("hold_reasons")) if str(x))
    dst["persisted"].update(str(x) for x in _as_list(row.get("persisted")) if str(x))
    dst["event_roots"].update(str(x) for x in _as_list(row.get("event_roots")) if str(x))
    dst["roots"].add(root)
    if row.get("last_seen_at"):
        dst["last_seen_at"].append(str(row.get("last_seen_at")))
    if row.get("median_drain_time_s") is not None:
        try:
            dst["median_drain_time_s"].append(float(row.get("median_drain_time_s")))
        except (TypeError, ValueError):
            pass
    if row.get("superseded_by"):
        dst["superseded_by"].add(str(row.get("superseded_by")))
    if row.get("superseded_reason"):
        dst["superseded_reason"].add(str(row.get("superseded_reason")))

    for key in [
        "ratified_proof_closure",
        "exact_gap",
        "valid_falsifier",
        "heldout_attempts",
        "heldout_successes",
        "seed_hold",
        "negative_controls_expected_fail",
        "negative_controls_unexpected_pass",
        "false_ratifications",
        "source_credit_eligible_ratifications",
        "clean_solver_credit_eligible_ratifications",
    ]:
        dst[key] = max(_as_int(dst[key]), _as_int(row.get(key)))


def _materialize_family(fam: dict[str, Any]) -> dict[str, Any]:
    fam["ratified_proof_closure"] = max(
        _as_int(fam["ratified_proof_closure"]),
        len(fam["ratified_rows"]),
        len(fam["persisted"]),
    )
    fam["exact_gap"] = max(_as_int(fam["exact_gap"]), len(fam["exact_gap_rows"]))
    fam["valid_falsifier"] = max(_as_int(fam["valid_falsifier"]), len(fam["valid_falsifier_rows"]))
    fam["heldout_successes"] = max(_as_int(fam["heldout_successes"]), len(fam["heldout_rows"]))
    useful = _as_int(fam["ratified_proof_closure"]) + _as_int(fam["exact_gap"]) + _as_int(fam["valid_falsifier"])
    neg_total = _as_int(fam["negative_controls_expected_fail"]) + _as_int(fam["negative_controls_unexpected_pass"])
    status, reason = _status(fam)
    medians = [float(x) for x in fam["median_drain_time_s"] if float(x) >= 0]
    return {
        "family": fam["family"],
        "status": status,
        "status_reason": reason,
        "rows_attempted": sorted(fam["rows_attempted"]),
        "unique_rows_attempted": len(fam["rows_attempted"]),
        "ratified_rows": sorted(fam["ratified_rows"]),
        "unique_ratified_rows": len(fam["ratified_rows"]),
        "ratified_proof_closure": _as_int(fam["ratified_proof_closure"]),
        "exact_gap": _as_int(fam["exact_gap"]),
        "valid_falsifier": _as_int(fam["valid_falsifier"]),
        "useful_outcomes": useful,
        "attempted_siblings": max(0, len(fam["rows_attempted"]) - 1),
        "heldout_attempts": _as_int(fam["heldout_attempts"]),
        "heldout_successes": _as_int(fam["heldout_successes"]),
        "heldout_rows": sorted(fam["heldout_rows"]),
        "median_drain_time_s": round(statistics.median(medians), 3) if medians else None,
        "negative_control_pass_rate": (
            round(float(_as_int(fam["negative_controls_unexpected_pass"])) / float(neg_total), 6)
            if neg_total else 0.0
        ),
        "last_seen_at": max(fam["last_seen_at"]) if fam["last_seen_at"] else "",
        "next_required_evidence": _next_required(status),
        "seed_hold": _as_int(fam["seed_hold"]),
        "hold_reasons": sorted(fam["hold_reasons"]),
        "superseded_by": sorted(fam["superseded_by"])[0] if fam["superseded_by"] else "",
        "superseded_reason": sorted(fam["superseded_reason"])[0] if fam["superseded_reason"] else "",
        "negative_controls_expected_fail": _as_int(fam["negative_controls_expected_fail"]),
        "negative_controls_unexpected_pass": _as_int(fam["negative_controls_unexpected_pass"]),
        "false_ratifications": _as_int(fam["false_ratifications"]),
        "source_credit_eligible_ratifications": _as_int(fam["source_credit_eligible_ratifications"]),
        "clean_solver_credit_eligible_ratifications": _as_int(fam["clean_solver_credit_eligible_ratifications"]),
        "persisted": sorted(fam["persisted"]),
        "event_roots": sorted(fam["event_roots"]),
        "converged_from_roots": sorted(fam["roots"]),
    }


def converge(paths: list[Path], *, out: Path | None = None, receipt: Path | None = None) -> dict[str, Any]:
    source_summaries: list[dict[str, Any]] = []
    families: dict[str, dict[str, Any]] = {}
    for path in paths:
        obj = _read_json(path)
        if obj.get("schema") != SCHEMA:
            raise ValueError(f"{path} has unsupported registry schema {obj.get('schema')!r}")
        source_summaries.append({
            "path": str(path),
            "sha256": _sha256(path),
            "family_count": _as_int(obj.get("family_count")),
            "status_counts": obj.get("status_counts") if isinstance(obj.get("status_counts"), dict) else {},
        })
        for row in _as_list(obj.get("families")):
            family = str(row.get("family") or "")
            if not family:
                continue
            dst = families.setdefault(family, _new_family(family))
            _merge_family(dst, row, root=str(path))

    family_rows = [_materialize_family(fam) for fam in families.values()]
    family_rows.sort(
        key=lambda r: (
            {
                "validated_family": 0,
                "validated_family_requires_true_holdout_check": 1,
                "candidate_family": 2,
                "seed_only": 3,
                "seed_hold": 4,
                "inventory_only": 5,
                "superseded_family": 6,
                "invalid_or_regression": 7,
            }.get(str(r["status"]), 9),
            -_as_int(r["ratified_proof_closure"]),
            str(r["family"]),
        )
    )
    status_counts: dict[str, int] = {}
    for row in family_rows:
        status_counts[str(row["status"])] = status_counts.get(str(row["status"]), 0) + 1

    payload = {
        "schema": SCHEMA,
        "roots": [s["path"] for s in source_summaries],
        "discovery": {
            "mode": "registry_convergence",
            "source_registries": source_summaries,
        },
        "closed_events": max((_as_int(_read_json(path).get("closed_events")) for path in paths), default=0),
        "duplicate_closed_events_ignored": 0,
        "negative_control_events": max((_as_int(_read_json(path).get("negative_control_events")) for path in paths), default=0),
        "decision_events": max((_as_int(_read_json(path).get("decision_events")) for path in paths), default=0),
        "heldout_receipt_events": max((_as_int(_read_json(path).get("heldout_receipt_events")) for path in paths), default=0),
        "family_count": len(family_rows),
        "status_counts": status_counts,
        "promotion_rules": {
            "seed_only": ">=1 governed useful outcome and no failed controls",
            "candidate_family": ">=2 useful outcomes across >=2 rows, >=1 expected-failing negative control, 0 unexpected negative passes, 0 false ratifications",
            "seed_hold": "sibling/heldout sourcing was checked and no promotable row is currently available",
            "validated_family_requires_true_holdout_check": ">=3 useful outcomes across >=2 rows and >=5 attempted rows, but event streams do not prove heldout independence",
            "validated_family": "candidate-family evidence plus >=1 passing heldout-independence receipt",
        },
        "convergence": {
            "schema": RECEIPT_SCHEMA,
            "source_registries": source_summaries,
        },
        "families": family_rows,
    }
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if receipt:
        receipt_obj = {
            "schema": RECEIPT_SCHEMA,
            "source_registries": source_summaries,
            "output": {
                "path": str(out) if out else "",
                "sha256": _sha256(out) if out and out.exists() else "",
                "family_count": len(family_rows),
                "status_counts": status_counts,
            },
            "changed_family_count": len(family_rows),
            "families": [
                {
                    "family": row["family"],
                    "status": row["status"],
                    "useful_outcomes": row["useful_outcomes"],
                    "negative_controls_unexpected_pass": row["negative_controls_unexpected_pass"],
                    "converged_from_roots": row["converged_from_roots"],
                }
                for row in family_rows
            ],
        }
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(receipt_obj, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        a = {
            "schema": SCHEMA,
            "family_count": 1,
            "status_counts": {"seed_only": 1},
            "families": [{
                "family": "fam",
                "status": "seed_only",
                "rows_attempted": ["r1"],
                "ratified_rows": ["r1"],
                "ratified_proof_closure": 1,
                "negative_controls_expected_fail": 1,
                "negative_controls_unexpected_pass": 0,
                "false_ratifications": 0,
                "persisted": ["/tmp/a.lean"],
            }],
        }
        b = {
            "schema": SCHEMA,
            "family_count": 1,
            "status_counts": {"seed_only": 1},
            "families": [{
                "family": "fam",
                "status": "seed_only",
                "rows_attempted": ["r2"],
                "ratified_rows": ["r2"],
                "ratified_proof_closure": 1,
                "negative_controls_expected_fail": 1,
                "negative_controls_unexpected_pass": 0,
                "false_ratifications": 0,
                "persisted": ["/tmp/b.lean"],
            }],
        }
        c = {
            "schema": SCHEMA,
            "family_count": 1,
            "status_counts": {"invalid_or_regression": 1},
            "families": [{
                "family": "bad",
                "status": "invalid_or_regression",
                "rows_attempted": ["r3"],
                "ratified_rows": ["r3"],
                "ratified_proof_closure": 1,
                "negative_controls_expected_fail": 0,
                "negative_controls_unexpected_pass": 1,
                "false_ratifications": 0,
            }],
        }
        paths = []
        for name, obj in [("a.json", a), ("b.json", b), ("c.json", c)]:
            path = root / name
            path.write_text(json.dumps(obj) + "\n")
            paths.append(path)
        out = root / "merged.json"
        receipt = root / "receipt.json"
        merged = converge(paths, out=out, receipt=receipt)
        by_family = {row["family"]: row for row in merged["families"]}
        assert by_family["fam"]["status"] == "candidate_family", merged
        assert by_family["fam"]["ratified_proof_closure"] == 2, merged
        assert by_family["bad"]["status"] == "invalid_or_regression", merged
        assert receipt.exists(), merged
    print("leanmill_registry_converger self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", action="append", required=False, default=[])
    ap.add_argument("--out")
    ap.add_argument("--receipt")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    paths = [Path(p) for p in args.registry]
    if len(paths) < 1:
        raise SystemExit("--registry is required")
    result = converge(paths, out=Path(args.out) if args.out else None, receipt=Path(args.receipt) if args.receipt else None)
    if args.quiet:
        print(json.dumps({
            "schema": result.get("schema"),
            "family_count": result.get("family_count"),
            "status_counts": result.get("status_counts"),
            "out": args.out or "",
            "receipt": args.receipt or "",
        }, sort_keys=True))
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
