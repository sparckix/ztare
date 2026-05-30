#!/usr/bin/env python3
"""Mine static-tool failures that match LeanMill repair-family signatures.

Pipeline stage: broad row pool -> static tool sweep -> static failures ->
repair-family signature matches. It deliberately does not run Path C, build
repair canaries, or credit proof value. Its output is supply for a later
canary-builder/freezer stage.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

import leanmill_evaluation_harness_runner as harness
import leanmill_family_specs as family_specs
from leanmill_paths import DATA_DIR

DEFAULT_ROW_CONTEXT = f"{DATA_DIR}/evaluation_harness_row_context_selected.json"
DEFAULT_SPEC_DIR = family_specs.DEFAULT_SPEC_DIR
DEFAULT_CHECKPOINT = f"{DATA_DIR}/static_failure_miner_checkpoint.jsonl"
DEFAULT_OUT = f"{DATA_DIR}/static_failure_miner_report.json"
DEFAULT_MD = f"{DATA_DIR}/static_failure_miner_report.md"
POSITIVE_EXITS = {
    "raw_closure_candidate",
    "governed_tool_tactic_closure_candidate",
    "ratified_closure",
    "exact_gap",
    "valid_falsifier",
}
STRICT_NO_SIGNAL_EXITS = {
    "tested_no_positive_signal",
}
INFRA_HOLD_EXITS = {
    "harness_candidate_build_failure",
    "harness_no_candidates",
    "target_kind_audit_failure",
    "wall_timeout_hit",
}
TARGET_REFERENCE_TEMPLATE_FAILURES = {
    "positive_template_references_target_theorem",
    "negative_control_references_target_theorem",
}
GENERIC_SIGNATURE_TOKENS = {
    "a", "ae", "all", "and", "at", "bound", "case", "closed", "dense",
    "differentiable", "domain", "eq", "exists", "exp", "finite", "for",
    "function", "has", "in", "inner", "integral", "left", "lt", "map",
    "measure", "mul", "neg", "nonneg", "norm", "of", "on", "one", "open",
    "pos", "real", "right", "set", "smul", "sub", "sum", "the", "top",
    "two", "zero",
}

STATIC_ROUTE = [
    {"tool_id": "exact?", "tactic": "exact?", "default_timeout_s": 20},
    {"tool_id": "apply?", "tactic": "apply?", "default_timeout_s": 20},
    {"tool_id": "simp_all", "tactic": "simp_all", "default_timeout_s": 20},
    {"tool_id": "aesop", "tactic": "aesop", "default_timeout_s": 30},
    {"tool_id": "hammer", "tactic": "hammer", "default_timeout_s": 60},
    {"tool_id": "duper", "tactic": "duper", "default_timeout_s": 45},
    {"tool_id": "auto", "tactic": "auto", "default_timeout_s": 45},
    {"tool_id": "omega", "tactic": "omega", "default_timeout_s": 20},
    {"tool_id": "norm_num", "tactic": "norm_num", "default_timeout_s": 20},
]


class _Args:
    def __init__(self, fallback_budget: int, per_candidate_timeout_s: int):
        self.residual_fallback_family_call_budget = fallback_budget
        self.per_candidate_timeout_s = per_candidate_timeout_s


def _read_json(path: str | Path) -> Any:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return None


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in p.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _append_jsonl(path: str | Path, rec: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
        fcntl.flock(fh, fcntl.LOCK_UN)


def _lease_path(checkpoint: str | Path, row_id: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in row_id) or "row"
    return Path(str(checkpoint) + ".leases") / f"{safe}.json"


def _claim_row_lease(checkpoint: str | Path, row_id: str, run_id: str, ttl_s: int) -> tuple[bool, str]:
    path = _lease_path(checkpoint, row_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    lease = {
        "schema": "leanmill-static-failure-row-lease-v1",
        "row_id": row_id,
        "run_id": run_id,
        "pid": os.getpid(),
        "claimed_at_epoch": int(now),
        "expires_at_epoch": int(now + max(60, int(ttl_s))),
    }
    fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        with os.fdopen(fd, "r+") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            raw = fh.read()
            current = None
            if raw.strip():
                try:
                    current = json.loads(raw)
                except json.JSONDecodeError:
                    current = None
            if isinstance(current, dict) and int(current.get("expires_at_epoch") or 0) > int(now):
                holder = str(current.get("run_id") or "unknown")
                fcntl.flock(fh, fcntl.LOCK_UN)
                return False, holder
            fh.seek(0)
            fh.truncate()
            fh.write(json.dumps(lease, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
            fcntl.flock(fh, fcntl.LOCK_UN)
            return True, str(path)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise


def _release_row_lease(checkpoint: str | Path, row_id: str, run_id: str) -> None:
    path = _lease_path(checkpoint, row_id)
    if not path.exists():
        return
    try:
        with path.open("r+") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                current = json.loads(fh.read() or "{}")
            except json.JSONDecodeError:
                current = {}
            if str(current.get("run_id") or "") == str(run_id):
                fh.seek(0)
                fh.truncate()
                fh.write(json.dumps({
                    "schema": "leanmill-static-failure-row-lease-v1",
                    "row_id": row_id,
                    "run_id": run_id,
                    "released_at_epoch": int(time.time()),
                    "expires_at_epoch": 0,
                }, sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            fcntl.flock(fh, fcntl.LOCK_UN)
    except OSError:
        return


def _row_id(row: dict[str, Any]) -> str:
    return str(row.get("row_id") or row.get("id") or row.get("target_id") or "")


def _iter_rows(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        raw = [x for x in obj if isinstance(x, dict)]
    elif isinstance(obj, dict):
        raw = []
        for key in ("rows", "results", "row_results", "qualified_rows", "items", "corpus"):
            vals = obj.get(key)
            if isinstance(vals, list):
                raw.extend(x for x in vals if isinstance(x, dict))
        for val in obj.values():
            if isinstance(val, dict) and _row_id(val):
                raw.append(val)
    else:
        raw = []
    out: dict[str, dict[str, Any]] = {}
    for row in raw:
        rid = _row_id(row)
        if rid:
            rec = dict(row)
            rec["row_id"] = rid
            if not rec.get("source_file") and rec.get("sorried_file"):
                rec["source_file"] = rec.get("sorried_file")
            out.setdefault(rid, rec)
    return list(out.values())


def _completed_ids(records: list[dict[str, Any]], run_id: str, *, any_run: bool = False) -> set[str]:
    out: set[str] = set()
    for rec in records:
        row_id = str(rec.get("row_id") or "")
        if not row_id:
            continue
        if any_run or str(rec.get("run_id") or "") == run_id:
            out.add(row_id)
    return out


def _haystack(row: dict[str, Any]) -> str:
    parts = [str(row.get(k) or "") for k in ("row_id", "goal", "target_theorem_name", "source_file", "status")]
    source_file = Path(str(row.get("source_file") or ""))
    if source_file.exists() and source_file.is_file():
        try:
            text = source_file.read_text(errors="ignore")
            target_line = int(row.get("target_line") or 0)
            if target_line > 0:
                lines = text.splitlines()
                start = max(0, target_line - 20)
                end = min(len(lines), target_line + 60)
                parts.append("\n".join(lines[start:end]))
            else:
                parts.append(text[:3000])
        except OSError:
            pass
        except (TypeError, ValueError):
            try:
                parts.append(source_file.read_text(errors="ignore")[:3000])
            except OSError:
                pass
    return "\n".join(parts)


def _family_signatures(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for spec in specs:
        family = str(spec.get("family") or "")
        if not family:
            continue
        residual = spec.get("residual_match") if isinstance(spec.get("residual_match"), dict) else {}
        patterns = [str(x) for x in residual.get("head_patterns") or [] if str(x)]
        lanes = [str(x) for x in residual.get("lanes") or [] if str(x)]
        classes = [str(x) for x in residual.get("residual_classes") or [] if str(x)]
        positive_rows = []
        negative_rows = []
        for template in spec.get("templates") or []:
            if not isinstance(template, dict):
                continue
            row_id = str(template.get("row_id") or "")
            if str(template.get("test_kind") or "") == "positive" and row_id:
                positive_rows.append(row_id)
            elif str(template.get("test_kind") or "") == "negative_control" and row_id:
                negative_rows.append(row_id)
        out.append({
            "family": family,
            "status": str(spec.get("status") or ""),
            "patterns": patterns,
            "lanes": lanes,
            "residual_classes": classes,
            "positive_rows": sorted(set(positive_rows)),
            "negative_rows": sorted(set(negative_rows)),
            "has_negative_controls": bool(negative_rows),
        })
    return out


def _target_reference_quarantine_count(specs: list[dict[str, Any]], target_names_by_row: dict[str, list[str]]) -> int:
    return sum(
        1
        for failure in family_specs.validate_specs(specs, target_names_by_row=target_names_by_row)
        if str(failure.get("failure") or "") in TARGET_REFERENCE_TEMPLATE_FAILURES
    )


def _distinctive(pattern: str) -> bool:
    token = pattern.strip().lower()
    if not token or token in GENERIC_SIGNATURE_TOKENS:
        return False
    if len(token) < 4 and "_" not in token and "." not in token:
        return False
    return True


def _match_families(row: dict[str, Any], signatures: list[dict[str, Any]], *, min_hits: int) -> list[dict[str, Any]]:
    hay = _haystack(row).lower()
    matches = []
    for sig in signatures:
        distinctive_hits = []
        generic_hits = []
        for pattern in sig["patterns"]:
            token = pattern.lower()
            if not token:
                continue
            if not re.search(r"(?<![A-Za-z0-9_])" + re.escape(token) + r"(?![A-Za-z0-9_])", hay):
                continue
            if _distinctive(pattern):
                distinctive_hits.append(pattern)
            else:
                generic_hits.append(pattern)
        if len(distinctive_hits) >= min_hits:
            matches.append({
                "family": sig["family"],
                "status": sig["status"],
                "matched_features": distinctive_hits[:12],
                "generic_features_ignored": generic_hits[:12],
                "hit_count": len(distinctive_hits),
                "confidence": round(min(0.95, 0.35 + 0.12 * len(distinctive_hits)), 3),
                "has_negative_controls": sig["has_negative_controls"],
                "template_design_rows": sig["positive_rows"][:10],
            })
    matches.sort(key=lambda item: (-int(item["hit_count"]), str(item["family"])))
    return matches


def _is_positive(rec: dict[str, Any]) -> bool:
    return str(rec.get("learning_exit") or "") in POSITIVE_EXITS


def _is_strict_no_signal(rec: dict[str, Any]) -> bool:
    return str(rec.get("learning_exit") or "") in STRICT_NO_SIGNAL_EXITS


def _is_infra_hold(rec: dict[str, Any]) -> bool:
    return str(rec.get("learning_exit") or "") in INFRA_HOLD_EXITS


def _run_static(row: dict[str, Any], args: argparse.Namespace, run_root: Path) -> dict[str, Any]:
    arm = {"arm": "public_tool_static", "route": STATIC_ROUTE, "uses_governance_gate": False, "uses_residual_memory": False}
    return harness._run_row_arm(
        _Args(0, int(args.per_candidate_timeout_s)),
        row=row,
        arm=arm,
        specs=[],
        max_calls=int(args.max_tool_calls),
        run_root=run_root,
        wall_timeout_s=int(args.wall_timeout_s),
    )


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    records = _read_jsonl(args.checkpoint)
    rows = _iter_rows(_read_json(args.row_context) or {})
    raw_specs = family_specs.load_specs(args.spec_dir)
    target_names_by_row = family_specs.target_names_by_row_from_context_paths([args.row_context])
    usable_specs = family_specs.usable_specs(raw_specs, target_names_by_row=target_names_by_row)
    signatures = _family_signatures(usable_specs)
    completed = _completed_ids(records, args.run_id, any_run=bool(args.skip_any_checkpoint_row))
    run_root = Path(args.run_root)
    started = time.time()
    wall_timeout_hit = False
    ran = 0
    lease_skipped = 0
    for row in rows[: max(0, int(args.limit))]:
        if (not args.no_run) and int(args.wall_timeout_s) > 0 and time.time() - started >= int(args.wall_timeout_s):
            wall_timeout_hit = True
            break
        row_id = _row_id(row)
        if bool(args.skip_any_checkpoint_row):
            completed = _completed_ids(_read_jsonl(args.checkpoint), args.run_id, any_run=True)
        if not row_id or row_id in completed:
            continue
        if args.no_run:
            continue
        claimed, holder = _claim_row_lease(args.checkpoint, row_id, args.run_id, int(args.lease_ttl_s))
        if not claimed:
            lease_skipped += 1
            continue
        try:
            if bool(args.skip_any_checkpoint_row) and row_id in _completed_ids(_read_jsonl(args.checkpoint), args.run_id, any_run=True):
                continue
            rec = _run_static(row, args, run_root)
            rec["run_id"] = args.run_id
            rec["miner_schema"] = "leanmill-static-failure-miner-record-v1"
            strict_no_signal = _is_strict_no_signal(rec)
            rec["family_matches"] = _match_families(row, signatures, min_hits=int(args.min_signature_hits)) if strict_no_signal else []
            rec["static_failure_class"] = (
                "positive" if _is_positive(rec) else
                "strict_no_signal" if strict_no_signal else
                "infra_hold" if _is_infra_hold(rec) else
                "other_non_positive"
            )
            rec["supply_candidate"] = strict_no_signal and any(m.get("has_negative_controls") for m in rec["family_matches"])
            rec["row_lease_receipt"] = {"status": "claimed", "lease_holder": holder}
            _append_jsonl(args.checkpoint, rec)
            records.append(rec)
            completed.add(row_id)
            ran += 1
        finally:
            _release_row_lease(args.checkpoint, row_id, args.run_id)
        if ran >= int(args.max_new_rows):
            break
    by_row: dict[str, dict[str, Any]] = {}
    for rec in records:
        if str(rec.get("run_id") or "") != args.run_id:
            continue
        row_id = str(rec.get("row_id") or "")
        if not row_id:
            continue
        # Existing four-arm benchmark checkpoints contain one record per arm;
        # for supply mining, the static/public arm is the source of truth.
        if str(rec.get("arm") or "") == "public_tool_static":
            by_row[row_id] = rec
        elif row_id not in by_row and not str(rec.get("arm") or ""):
            by_row[row_id] = rec
    candidates = []
    counts = Counter()
    for row in rows:
        row_id = _row_id(row)
        rec = by_row.get(row_id)
        if not rec:
            continue
        exit_kind = str(rec.get("learning_exit") or "")
        positive = _is_positive(rec)
        strict_no_signal = _is_strict_no_signal(rec)
        infra_hold = _is_infra_hold(rec)
        if positive:
            counts["static_positive"] += 1
        elif strict_no_signal:
            counts["static_fail_or_no_signal"] += 1
        elif infra_hold:
            counts["static_harness_infra_hold"] += 1
        else:
            counts["static_other_non_positive"] += 1
        matches = rec.get("family_matches") or (_match_families(row, signatures, min_hits=int(args.min_signature_hits)) if strict_no_signal else [])
        if positive:
            continue
        if strict_no_signal and matches:
            counts["static_fail_family_matched"] += 1
        if strict_no_signal and any(m.get("has_negative_controls") for m in matches):
            counts["static_fail_family_matched_with_negative_controls"] += 1
        candidates.append({
            "row_id": row_id,
            "static_result": exit_kind,
            "static_failure_class": (
                "strict_no_signal" if strict_no_signal else
                "infra_hold" if infra_hold else
                "other_non_positive"
            ),
            "attempt_count": rec.get("attempt_count"),
            "wall_time_used_s": rec.get("wall_time_used_s"),
            "source_file": row.get("source_file"),
            "family_matches": matches[:8],
            "supply_candidate": bool(strict_no_signal and matches and any(m.get("has_negative_controls") for m in matches)),
        })
    candidates.sort(key=lambda item: (
        not bool(item.get("supply_candidate")),
        -max([int(m.get("hit_count") or 0) for m in item.get("family_matches") or []] or [0]),
        str(item.get("row_id") or ""),
    ))
    result = {
        "schema": "leanmill-static-failure-miner-report-v1",
        "run_id": args.run_id,
        "row_context": args.row_context,
        "checkpoint": args.checkpoint,
        "spec_dir": args.spec_dir,
        "no_run": bool(args.no_run),
        "rows_seen": len(rows),
        "new_rows_run": ran,
        "elapsed_s": round(time.time() - started, 3),
        "wall_timeout_hit": wall_timeout_hit,
        "lease_skipped_count": lease_skipped,
        "target_aware_family_template_filter": {
            "target_context_row_count": len(target_names_by_row),
            "target_reference_quarantine_count": _target_reference_quarantine_count(raw_specs, target_names_by_row),
            "usable_family_signature_count": len(signatures),
            "rationale": "static-failure family signatures are computed after row-target quarantine",
        },
        "counts": dict(counts),
        "supply_candidate_count": sum(1 for c in candidates if c.get("supply_candidate")),
        "candidates": candidates[: int(args.report_limit)],
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if args.md:
        _write_md(args.md, result)
    return result


def _write_md(path: str | Path, result: dict[str, Any]) -> None:
    lines = [
        "# LeanMill Static Failure Miner",
        "",
        f"- run_id: `{result['run_id']}`",
        f"- rows seen: `{result['rows_seen']}`",
        f"- new rows run: `{result['new_rows_run']}`",
        f"- counts: `{result['counts']}`",
        f"- supply candidates: `{result['supply_candidate_count']}`",
        "",
        "## Candidates",
        "",
        "| row | static | supply | families |",
        "|---|---|---:|---|",
    ]
    for cand in result["candidates"]:
        fams = ",".join(m["family"] for m in cand.get("family_matches") or [])
        lines.append("| " + " | ".join([str(cand["row_id"]), str(cand["static_result"]), str(cand["supply_candidate"]), fams]) + " |")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n")


def _self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="leanmill_static_miner_") as td:
        root = Path(td)
        spec_dir = root / "specs"
        spec_dir.mkdir()
        (spec_dir / "fam.yaml").write_text("""
family: fam
status: candidate_family
residual_match:
  head_patterns: [AlphaToken, BetaToken]
templates:
  - id: pos
    row_id: design
    test_kind: positive
    body_lines: [trivial]
  - id: neg
    row_id: design
    test_kind: negative_control
    body_lines: [exact False.elim]
""")
        (spec_dir / "leaky.yaml").write_text("""
family: leaky
status: candidate_family
residual_match:
  head_patterns: [AlphaToken, BetaToken]
templates:
  - id: pos
    row_id: design
    test_kind: positive
    body_lines: [exact design]
  - id: neg
    row_id: design
    test_kind: negative_control
    body_lines: [trivial]
""")
        src = root / "r.lean"
        src.write_text("theorem r : True := by\n  trivial\n-- AlphaToken BetaToken\n")
        rows = root / "rows.json"
        rows.write_text(json.dumps({"rows": [
            {"row_id": "r", "source_file": str(src), "goal": "theorem r : True := by AlphaToken"},
            {"row_id": "design", "target_theorem_name": "design", "source_file": str(src)},
        ]}) + "\n")
        ck = root / "ck.jsonl"
        ck.write_text(json.dumps({"run_id": "x", "row_id": "r", "learning_exit": "tested_no_positive_signal", "attempt_count": 2}) + "\n")
        result = build_report(argparse.Namespace(
            row_context=str(rows),
            spec_dir=str(spec_dir),
            checkpoint=str(ck),
            out=None,
            md=None,
            run_id="x",
            run_root=str(root / "run"),
            limit=10,
            max_new_rows=0,
            max_tool_calls=3,
            per_candidate_timeout_s=5,
            wall_timeout_s=20,
            min_signature_hits=2,
            report_limit=20,
            no_run=True,
            skip_any_checkpoint_row=False,
            lease_ttl_s=120,
        ))
        assert result["supply_candidate_count"] == 1, result
        assert result["candidates"][0]["family_matches"][0]["family"] == "fam", result
        assert [m["family"] for m in result["candidates"][0]["family_matches"]] == ["fam"], result
        assert result["target_aware_family_template_filter"]["target_reference_quarantine_count"] == 1, result
        ck.write_text(json.dumps({"run_id": "infra", "row_id": "r", "learning_exit": "harness_candidate_build_failure", "attempt_count": 2}) + "\n")
        infra = build_report(argparse.Namespace(
            row_context=str(rows),
            spec_dir=str(spec_dir),
            checkpoint=str(ck),
            out=None,
            md=None,
            run_id="infra",
            run_root=str(root / "run"),
            limit=10,
            max_new_rows=0,
            max_tool_calls=3,
            per_candidate_timeout_s=5,
            wall_timeout_s=20,
            min_signature_hits=2,
            report_limit=20,
            no_run=True,
            skip_any_checkpoint_row=False,
            lease_ttl_s=120,
        ))
        assert infra["counts"]["static_harness_infra_hold"] == 1, infra
        assert infra["supply_candidate_count"] == 0, infra
        assert infra["candidates"][0]["static_failure_class"] == "infra_hold", infra
    print("leanmill_static_failure_miner self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--row-context", default=DEFAULT_ROW_CONTEXT)
    ap.add_argument("--spec-dir", default=DEFAULT_SPEC_DIR)
    ap.add_argument("--checkpoint", default=DEFAULT_CHECKPOINT)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--md", default=DEFAULT_MD)
    ap.add_argument("--run-id", default="static_failure_miner")
    ap.add_argument("--run-root", default="/tmp/rung1/leanmill_static_failure_miner")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--max-new-rows", type=int, default=20)
    ap.add_argument("--max-tool-calls", type=int, default=9)
    ap.add_argument("--per-candidate-timeout-s", type=int, default=30)
    ap.add_argument("--wall-timeout-s", type=int, default=180)
    ap.add_argument("--min-signature-hits", type=int, default=2, help="minimum distinctive, non-generic family-signature hits")
    ap.add_argument("--report-limit", type=int, default=80)
    ap.add_argument("--no-run", action="store_true")
    ap.add_argument("--skip-any-checkpoint-row", action="store_true", help="skip a row once any prior checkpoint record exists, regardless of run_id")
    ap.add_argument("--lease-ttl-s", type=int, default=1800, help="stale lease timeout for cross-process row claims")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    result = build_report(args)
    print(json.dumps({
        "out": args.out,
        "md": args.md,
        "checkpoint": args.checkpoint,
        "new_rows_run": result["new_rows_run"],
        "counts": result["counts"],
        "supply_candidate_count": result["supply_candidate_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
