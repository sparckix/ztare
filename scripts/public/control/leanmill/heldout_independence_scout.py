#!/usr/bin/env python3
"""Scout independent heldout candidates for LeanMill repair families.

This worker does not promote families and does not create heldout receipts. It
only identifies rows that could be eligible for a heldout attempt under the
receipt gate's independence rules, then optionally queues bounded GM/operator
reviews for the highest-scoring candidates.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

import leanmill_family_specs as family_specs
import leanmill_work_queue as work_queue
from leanmill_factory_config import FACTORY_POLICY as DEFAULT_FACTORY_POLICY, priority_value


DEFAULT_DATA_DIR = "analytics/public/leanmill/dashboard_data"
DEFAULT_REGISTRY = f"{DEFAULT_DATA_DIR}/repair_family_registry.json"
DEFAULT_OUT = f"{DEFAULT_DATA_DIR}/heldout_independence_scout.json"
DEFAULT_MD = f"{DEFAULT_DATA_DIR}/heldout_independence_scout.md"
DEFAULT_CORPORA = [
    "/tmp/rung1/mcb_refill_dedup_after_expand100/mcb_corpus.json",
    "analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_QUEUE.json",
    "analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_ROW_CONTEXT_FILTER.json",
]
DEFAULT_MAX_CANDIDATES_PER_FAMILY = 8


def _priority_base(args: argparse.Namespace, key: str, fallback: int) -> int:
    return priority_value(
        path=getattr(args, "factory_policy", DEFAULT_FACTORY_POLICY),
        namespace="formula_bases",
        key=key,
        fallback=fallback,
    )


def _read_json(path: str | Path) -> Any:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}


def _rows_from_obj(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if not isinstance(obj, dict):
        return []
    for key in ("rows", "corpus_rows", "corpus", "records", "items"):
        vals = obj.get(key)
        if isinstance(vals, list):
            return [x for x in vals if isinstance(x, dict)]
    return []


def _row_id(row: dict[str, Any]) -> str:
    return str(row.get("row_id") or row.get("id") or row.get("name") or "")


def _source(row: dict[str, Any]) -> dict[str, str]:
    src = row.get("source") if isinstance(row.get("source"), dict) else {}
    mathlib_name = str(
        src.get("mathlib_name")
        or row.get("mathlib_name")
        or row.get("decl_name")
        or row.get("theorem")
        or row.get("name")
        or _row_id(row)
        or ""
    )
    source_file = str(src.get("file") or row.get("mathlib_file") or row.get("source_file") or row.get("sorried_file") or "")
    return {"mathlib_name": mathlib_name, "source_file": source_file}


def _name_from_row_id(row_id: str) -> str:
    return re.sub(r"^MCB_\d+_", "", str(row_id or "")).strip()


def _row_text(row: dict[str, Any]) -> str:
    src = _source(row)
    parts = [
        _row_id(row),
        src["mathlib_name"],
        src["source_file"],
        str(row.get("goal") or ""),
        str(row.get("type") or ""),
    ]
    return "\n".join(parts)


def _tokenize(value: str) -> set[str]:
    return {tok.lower() for tok in re.split(r"[^A-Za-z0-9']+", value) if len(tok) >= 3}


def _family_tokens(family: str) -> set[str]:
    stop = {"planner", "family", "repair", "source", "action"}
    return {tok for tok in _tokenize(family) if tok not in stop}


def _load_corpus(paths: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_id: dict[str, dict[str, Any]] = {}
    meta: list[dict[str, Any]] = []
    for path in paths:
        obj = _read_json(path)
        rows = _rows_from_obj(obj)
        meta.append({"path": path, "exists": Path(path).exists(), "row_count": len(rows)})
        for row in rows:
            rid = _row_id(row)
            if rid and rid not in by_id:
                by_id[rid] = row
    return list(by_id.values()), meta


def _family_spec_index(spec_dir: str) -> dict[str, dict[str, Any]]:
    return {str(spec.get("family") or ""): spec for spec in family_specs.load_specs(spec_dir)}


def _design_rows(family_rec: dict[str, Any], spec: dict[str, Any] | None) -> set[str]:
    rows = set(str(x) for x in (family_rec.get("rows_attempted") or family_rec.get("ratified_rows") or []) if str(x or ""))
    if spec:
        for template in spec.get("templates") or []:
            if isinstance(template, dict) and str(template.get("test_kind") or "positive") == "positive":
                row_id = str(template.get("row_id") or "")
                if row_id:
                    rows.add(row_id)
    return rows


def _head_patterns(family: str, spec: dict[str, Any] | None) -> set[str]:
    patterns = set(_family_tokens(family))
    if spec:
        match = spec.get("residual_match") if isinstance(spec.get("residual_match"), dict) else {}
        for val in match.get("head_patterns") or []:
            patterns.update(_tokenize(str(val)))
        for template in spec.get("templates") or []:
            if not isinstance(template, dict):
                continue
            patterns.update(_tokenize(str(template.get("id") or "")))
    return {p for p in patterns if len(p) >= 3}


def _score_row(row: dict[str, Any], *, family: str, spec: dict[str, Any] | None, design_files: set[str], design_names: set[str]) -> tuple[int, list[str]]:
    text = _row_text(row)
    lower = text.lower()
    score = 0
    reasons: list[str] = []
    for pat in sorted(_head_patterns(family, spec)):
        if pat.lower() in lower:
            score += 3
            reasons.append(f"pattern:{pat}")
    src = _source(row)
    source_file = src["source_file"]
    mathlib_name = src["mathlib_name"]
    if source_file and design_files:
        row_dirs = set(source_file.split("/")[:-1])
        design_dirs = {part for path in design_files for part in path.split("/")[:-1]}
        overlap = sorted(row_dirs & design_dirs)
        if overlap:
            score += min(4, len(overlap))
            reasons.append("directory_overlap:" + ",".join(overlap[:3]))
    name_tokens = _tokenize(mathlib_name)
    design_name_tokens = {tok for name in design_names for tok in _tokenize(name)}
    shared = sorted(name_tokens & design_name_tokens)
    if shared:
        score += min(6, 2 * len(shared))
        reasons.append("name_token_overlap:" + ",".join(shared[:4]))
    if score == 0:
        reasons.append("no_structural_overlap")
    return score, reasons


def _build_report(args: argparse.Namespace) -> dict[str, Any]:
    registry = _read_json(args.registry)
    specs = _family_spec_index(args.spec_dir)
    corpus, corpus_meta = _load_corpus(args.corpus)
    corpus_by_id = {_row_id(row): row for row in corpus if _row_id(row)}
    families: list[dict[str, Any]] = []
    for family_rec in registry.get("families") or []:
        family = str(family_rec.get("family") or "")
        if not family:
            continue
        status = str(family_rec.get("status") or "")
        next_required = str(family_rec.get("next_required_evidence") or "")
        if not args.include_seed_families and status != "candidate_family":
            continue
        if "heldout" not in next_required and status != "candidate_family":
            continue
        spec = specs.get(family)
        design_rows = _design_rows(family_rec, spec)
        design_records = [corpus_by_id[rid] for rid in sorted(design_rows) if rid in corpus_by_id]
        design_files = {_source(row)["source_file"] for row in design_records if _source(row)["source_file"]}
        design_names = {_source(row)["mathlib_name"] for row in design_records if _source(row)["mathlib_name"]}
        design_names.update(_name_from_row_id(rid) for rid in design_rows if _name_from_row_id(rid))
        candidates: list[dict[str, Any]] = []
        blockers: list[str] = []
        if not design_rows:
            blockers.append("missing_design_rows")
        if not design_records:
            blockers.append("design_rows_not_found_in_corpus")
        if not design_files:
            blockers.append("missing_design_source_files")
        for row in corpus:
            rid = _row_id(row)
            if not rid or rid in design_rows:
                continue
            src = _source(row)
            if src["source_file"] and src["source_file"] in design_files:
                continue
            if src["mathlib_name"] and src["mathlib_name"] in design_names:
                continue
            score, reasons = _score_row(row, family=family, spec=spec, design_files=design_files, design_names=design_names)
            if score < args.min_score:
                continue
            candidates.append({
                "row_id": rid,
                "mathlib_name": src["mathlib_name"],
                "source_file": src["source_file"],
                "score": score,
                "reasons": reasons[:8],
                "independence_precheck": {
                    "not_same_row": True,
                    "not_same_target_alias": bool(src["mathlib_name"] and src["mathlib_name"] not in design_names),
                    "not_same_source_file": bool(src["source_file"] and src["source_file"] not in design_files),
                    "not_used_in_template_design": True,
                },
            })
        candidates.sort(key=lambda rec: (-int(rec["score"]), str(rec["row_id"])))
        candidates = candidates[: max(0, args.max_candidates_per_family)]
        if not candidates:
            blockers.append("no_independent_candidate_above_score_floor")
        families.append({
            "family": family,
            "status": status,
            "next_required_evidence": next_required,
            "design_rows": sorted(design_rows),
            "design_source_files": sorted(design_files),
            "eligible_candidate_count": len(candidates),
            "eligible_candidates": candidates,
            "blockers": sorted(set(blockers)),
            "spec_path": str((spec or {}).get("_path") or ""),
        })
    return {
        "schema": "leanmill-heldout-independence-scout-v1",
        "generated_at_epoch": int(time.time()),
        "registry": args.registry,
        "spec_dir": args.spec_dir,
        "corpus_meta": corpus_meta,
        "family_count": len(families),
        "eligible_family_count": sum(1 for fam in families if fam["eligible_candidate_count"] > 0),
        "families": families,
        "science_rule": "Scout results are eligibility hints only; validated-family promotion requires a passing heldout receipt and governance evidence.",
    }


def _write_md(payload: dict[str, Any], path: str) -> None:
    lines = [
        "# LeanMill Heldout Independence Scout",
        "",
        f"- generated_at_epoch: `{payload.get('generated_at_epoch')}`",
        f"- family_count: `{payload.get('family_count')}`",
        f"- eligible_family_count: `{payload.get('eligible_family_count')}`",
        "",
        "## Families",
    ]
    for fam in payload.get("families") or []:
        lines.extend([
            "",
            f"### {fam.get('family')}",
            f"- status: `{fam.get('status')}`",
            f"- next_required_evidence: `{fam.get('next_required_evidence')}`",
            f"- design_rows: `{', '.join(fam.get('design_rows') or [])}`",
            f"- design_source_files: `{', '.join(fam.get('design_source_files') or [])}`",
            f"- eligible_candidate_count: `{fam.get('eligible_candidate_count')}`",
            f"- blockers: `{', '.join(fam.get('blockers') or [])}`",
        ])
        for cand in (fam.get("eligible_candidates") or [])[:5]:
            lines.append(
                f"- candidate `{cand.get('row_id')}` `{cand.get('mathlib_name')}` "
                f"score={cand.get('score')} file=`{cand.get('source_file')}` reasons=`{', '.join(cand.get('reasons') or [])}`"
            )
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines).rstrip() + "\n")


def _open_same_task_exists(cx: Any, *, family: str, row_id: str) -> bool:
    rows = cx.execute(
        """
        SELECT payload_json
        FROM work_items
        WHERE kind='gm_operator_task' AND family=? AND status IN ('queued','claimed','running')
        """,
        (family,),
    ).fetchall()
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            continue
        if str(payload.get("heldout_candidate", {}).get("row_id") or "") == row_id:
            return True
    return False


def _enqueue_tasks(args: argparse.Namespace, payload: dict[str, Any]) -> list[dict[str, Any]]:
    cx = work_queue.connect(args.queue_db)
    run_id = args.run_id or str(int(time.time()))
    enqueued: list[dict[str, Any]] = []
    for fam in payload.get("families") or []:
        if len(enqueued) >= max(0, args.max_enqueued_tasks):
            break
        family = str(fam.get("family") or "")
        candidates = fam.get("eligible_candidates") or []
        if not family or not candidates:
            continue
        cand = candidates[0]
        row_id = str(cand.get("row_id") or "")
        if not row_id or _open_same_task_exists(cx, family=family, row_id=row_id):
            continue
        work_id = f"gm_heldout_scout:{family}:{row_id}:{run_id}"
        task = {
            "work_id": work_id,
            "family": family,
            "station": "repair_registry",
            "expected_exit": "gm_sibling_or_heldout_review",
            "task": (
                "Review this heldout scout candidate. Either produce a bounded heldout attempt plan with matched negative "
                "control requirements, or reject it with a concrete blocker. Do not create heldout receipts or proof credit."
            ),
            "heldout_candidate": cand,
            "design_rows": fam.get("design_rows") or [],
            "design_source_files": fam.get("design_source_files") or [],
            "credit_type": "none",
            "proof_credit_authority": "governance_gate",
            "worker_can_self_ratify": False,
        }
        work_queue.enqueue(
            cx,
            kind="gm_operator_task",
            priority=_priority_base(args, "heldout_independence_scout", 245) + int(cand.get("score") or 0),
            payload=task,
            max_attempts=1,
        )
        work_queue.append_event(args.events, {
            "event_type": "heldout_scout_gm_task_enqueued",
            "work_id": work_id,
            "payload": {
                "family": family,
                "heldout_candidate_row": row_id,
                "score": cand.get("score"),
            },
            "artifact_paths": [args.out, args.md],
        })
        enqueued.append({"work_id": work_id, "family": family, "row_id": row_id, "score": cand.get("score")})
    return enqueued


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="leanmill_heldout_scout_") as td:
        root = Path(td)
        corpus = root / "corpus.json"
        registry = root / "registry.json"
        spec_dir = root / "specs"
        spec_dir.mkdir()
        corpus.write_text(json.dumps({
            "rows": [
                {"id": "r1", "source": {"mathlib_name": "foo_transport", "file": "A/Foo.lean"}, "goal": "foo transport"},
                {"id": "r2", "source": {"mathlib_name": "foo_transport_sibling", "file": "B/FooSibling.lean"}, "goal": "foo transport sibling"},
                {"id": "r3", "source": {"mathlib_name": "bar", "file": "A/Foo.lean"}, "goal": "foo same file"},
                {"id": "r4", "source": {"mathlib_name": "same_target_alias", "file": "C/Foo.lean"}, "goal": "foo same alias"},
            ]
        }))
        registry.write_text(json.dumps({
            "families": [{
                "family": "foo_transport_planner",
                "status": "candidate_family",
                "next_required_evidence": "heldout_attempts_and_validated_family_receipt",
                "rows_attempted": ["r1", "MCB_999_same_target_alias"],
                "ratified_rows": ["r1", "MCB_999_same_target_alias"],
            }]
        }))
        (spec_dir / "foo.yaml").write_text(
            "family: foo_transport_planner\nversion: 1\nstatus: candidate_family\n"
            "residual_match:\n  head_patterns: [foo, transport]\n"
            "credit:\n  source_credit_eligible: false\n  clean_solver_credit_eligible: false\n"
            "templates:\n"
            "  - id: pos\n    row_id: r1\n    test_kind: positive\n    expected_outcome: governed_repair_canary_closure\n    backend: repl_file\n    timeout: 30\n    body: exact h\n"
            "  - id: neg\n    row_id: r1\n    test_kind: negative_control\n    expected_outcome: must_fail\n    backend: repl_file\n    timeout: 30\n    body: exact h\n"
        )
        args = argparse.Namespace(
            registry=str(registry),
            spec_dir=str(spec_dir),
            corpus=[str(corpus)],
            include_seed_families=False,
            max_candidates_per_family=5,
            min_score=1,
        )
        payload = _build_report(args)
        fam = payload["families"][0]
        assert fam["eligible_candidates"][0]["row_id"] == "r2", fam
        assert all(c["row_id"] != "r3" for c in fam["eligible_candidates"])
        assert all(c["row_id"] != "r4" for c in fam["eligible_candidates"])
    print("leanmill_heldout_independence_scout self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    ap.add_argument("--spec-dir", default=family_specs.DEFAULT_SPEC_DIR)
    ap.add_argument("--corpus", action="append", default=list(DEFAULT_CORPORA))
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--md", default=DEFAULT_MD)
    ap.add_argument("--max-candidates-per-family", type=int, default=DEFAULT_MAX_CANDIDATES_PER_FAMILY)
    ap.add_argument("--min-score", type=int, default=1)
    ap.add_argument("--include-seed-families", action="store_true")
    ap.add_argument("--enqueue-gm-tasks", action="store_true")
    ap.add_argument("--max-enqueued-tasks", type=int, default=4)
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--factory-policy", default=DEFAULT_FACTORY_POLICY)
    ap.add_argument("--run-id", default="")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    payload = _build_report(args)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    _write_md(payload, args.md)
    enqueued = _enqueue_tasks(args, payload) if args.enqueue_gm_tasks else []
    payload["enqueued_gm_tasks"] = enqueued
    Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "out": args.out,
        "md": args.md,
        "family_count": payload["family_count"],
        "eligible_family_count": payload["eligible_family_count"],
        "enqueued_gm_tasks": len(enqueued),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
