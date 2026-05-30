#!/usr/bin/env python3
"""Prepare LeanMill four-arm benchmark inputs without running the benchmark."""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import leanmill_de_experiment_contract as de_contract
import leanmill_family_specs as family_specs
import leanmill_source_materialization as source_materialization
from leanmill_factory_config import read_policy
from leanmill_paths import DATA_DIR, FACTORY_POLICY, REPAIR_FAMILY_REGISTRY


DEFAULT_ROW_CONTEXT = f"{DATA_DIR}/mcb_expand100/row_context_filter_fallback.json"
DEFAULT_CONTRACT = f"{DATA_DIR}/evaluation_harness_contract.json"
DEFAULT_OUT = f"{DATA_DIR}/evaluation_harness_prep.json"
DEFAULT_MD = f"{DATA_DIR}/evaluation_harness_prep.md"
DEFAULT_MERGED_ROW_CONTEXT = f"{DATA_DIR}/evaluation_harness_row_context_selected.json"
DEFAULT_DIAGNOSTICS = f"{DATA_DIR}/evaluation_harness_prep_diagnostics.json"
DEFAULT_SOURCE_SNAPSHOT_DIR = f"{DATA_DIR}/evaluation_harness_sources"
DEFAULT_SPEC_DIR = family_specs.DEFAULT_SPEC_DIR
ORDERED_TIERS = [
    "known_possible_controls",
    "family_spec_template_rows",
    "target_context_ready_tractable",
    "corrected_escape_route_rows",
    "repair_family_sibling_or_heldout",
    "hard_open_or_gap_candidates",
]
THEOREM_NAME_RE = re.compile(r"(?:^|\n)\s*(?:@[^\n]*\n\s*)*(?:public\s+|private\s+|protected\s+|noncomputable\s+|unsafe\s+)*\s*(?:theorem|lemma)\s+([^\s:]+)")
DECL_RE_TEMPLATE = (
    r"(^|\n)\s*(?:@[^\n]*\n\s*)*"
    r"(?:public\s+|private\s+|protected\s+|noncomputable\s+|unsafe\s+)*"
    r"(?:theorem|lemma)\s+{name}(?=\s|:)"
)
NEXT_TOP_DECL_RE = re.compile(
    r"\n\s*(?:@[^\n]*\n\s*)*"
    r"(?:public\s+|private\s+|protected\s+|noncomputable\s+|unsafe\s+|abbrev\s+)*"
    r"(?:theorem|lemma|def|abbrev|instance|structure|inductive|class)\s+"
)


def _read_json(path: str | Path) -> Any:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return None


def _row_id(row: dict[str, Any]) -> str:
    return str(row.get("row_id") or row.get("id") or row.get("target_id") or "")


def _append_unique(values: list[str], value: Any) -> None:
    item = str(value or "").strip()
    if item and item not in values:
        values.append(item)


def _row_theorem_name_candidates(row: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    source = row.get("source") if isinstance(row.get("source"), dict) else {}
    for key in ("mathlib_name", "theorem_name", "decl_name", "declaration_name", "target_name"):
        _append_unique(candidates, row.get(key))
        _append_unique(candidates, source.get(key))
    goal = str(row.get("goal") or "")
    match = THEOREM_NAME_RE.search(goal)
    if match:
        _append_unique(candidates, match.group(1))
    rid = _row_id(row)
    parts = rid.split("_", 2)
    _append_unique(candidates, parts[2] if len(parts) >= 3 else rid)
    return candidates


def _find_target_start(text: str, theorem_name: str) -> int:
    pattern = re.compile(
        rf"(^|\n)\s*(?:@[^\n]*\n\s*)*"
        rf"(?:public\s+|private\s+|protected\s+|noncomputable\s+|unsafe\s+)*"
        rf"(?:theorem|lemma)\s+{re.escape(theorem_name)}(?=\s|:)"
    )
    match = pattern.search(text)
    return -1 if not match else match.start(0) + (1 if match.group(1) else 0)


def _resolve_theorem_name(text: str, preferred: str) -> dict[str, Any]:
    if _find_target_start(text, preferred) >= 0:
        return {"status": "exact", "theorem_name": preferred}
    stem = preferred.rstrip("_")
    names = [m.group(1) for m in THEOREM_NAME_RE.finditer(text)]
    prefix_matches = [name for name in names if stem and name.startswith(stem)]
    if len(prefix_matches) == 1:
        return {"status": "prefix_unique", "theorem_name": prefix_matches[0], "preferred": preferred}
    if prefix_matches:
        return {"status": "ambiguous_prefix", "theorem_name": "", "preferred": preferred, "candidates": prefix_matches[:12]}
    if len(names) == 1:
        return {"status": "single_theorem_in_source", "theorem_name": names[0], "preferred": preferred}
    return {"status": "not_found", "theorem_name": "", "preferred": preferred, "candidates": names[:12]}


def _row_target_resolution(row: dict[str, Any]) -> dict[str, Any]:
    return source_materialization.row_target_resolution(row)


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in value).strip("_") or "row"


def _sha256_text(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _mathlib_root(args: argparse.Namespace | None = None) -> Path | None:
    configured = str(getattr(args, "mathlib_root", "") or "")
    candidates = [Path(configured)] if configured else []
    candidates.extend([
        Path("ztare_proofs/.lake/packages/mathlib/Mathlib"),
        Path(".lake/packages/mathlib/Mathlib"),
    ])
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def _find_decl_start(text: str, theorem_name: str) -> int:
    if not theorem_name:
        return -1
    pattern = re.compile(DECL_RE_TEMPLATE.format(name=re.escape(theorem_name)))
    match = pattern.search(text)
    return -1 if not match else match.start(0) + (1 if match.group(1) else 0)


def _replace_decl_body_with_sorry(src: str, theorem_name: str) -> dict[str, Any]:
    start = _find_decl_start(src, theorem_name)
    if start < 0:
        return {"status": "fail", "reason": "decl_not_found", "theorem_name": theorem_name}
    next_decl = NEXT_TOP_DECL_RE.search(src, start + 1)
    end = next_decl.start() + 1 if next_decl else len(src)
    block = src[start:end]
    depth = 0
    body_idx = -1
    i = 0
    while i < len(block) - 1:
        ch = block[i]
        if ch in "([{⟨":
            depth += 1
        elif ch in ")]}⟩" and depth > 0:
            depth -= 1
        elif depth == 0 and block[i:i + 2] == ":=":
            body_idx = i
            break
        i += 1
    if body_idx < 0:
        return {"status": "fail", "reason": "body_marker_not_found", "theorem_name": theorem_name}
    new_block = block[:body_idx].rstrip() + " := by\n  sorry\n"
    return {
        "status": "pass",
        "text": src[:start] + new_block + src[end:],
        "target_line": src[:start].count("\n") + 1,
        "theorem_name": theorem_name,
        "original_block_sha256": _sha256_text(block),
    }


def _materialize_source_from_mathlib(row: dict[str, Any], *, out_dir: str | Path, args: argparse.Namespace) -> dict[str, Any]:
    return source_materialization.materialize_source_from_mathlib(
        row,
        out_dir=out_dir,
        mathlib_root=getattr(args, "mathlib_root", ""),
    )


def _materialize_row_sources(rows: list[dict[str, Any]], *, out_dir: str | Path, args: argparse.Namespace) -> dict[str, Any]:
    return source_materialization.materialize_row_sources(
        rows,
        out_dir=out_dir,
        mathlib_root=getattr(args, "mathlib_root", ""),
    )


def _policy_operations(path: str | Path = FACTORY_POLICY) -> dict[str, Any]:
    policy = read_policy(path)
    ops = policy.get("operations") if isinstance(policy, dict) else {}
    return ops if isinstance(ops, dict) else {}


def _policy_int(key: str, fallback: int, *, path: str | Path = FACTORY_POLICY) -> int:
    try:
        return int(_policy_operations(path).get(key, fallback))
    except (TypeError, ValueError):
        return fallback


def _policy_list(key: str, *, path: str | Path = FACTORY_POLICY) -> list[str]:
    value = _policy_operations(path).get(key, [])
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def _template_rows_by_kind(
    specs: list[dict[str, Any]],
    *,
    test_kind: str,
    target_names_by_row: dict[str, list[str]] | None = None,
) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for spec in family_specs.usable_specs(specs, target_names_by_row=target_names_by_row):
        family = str(spec.get("family") or "")
        for template in spec.get("templates") or []:
            if not isinstance(template, dict):
                continue
            row_id = str(template.get("row_id") or "")
            if row_id and str(template.get("test_kind") or "") == test_kind:
                out.setdefault(row_id, set()).add(family)
    return out


def _positive_template_rows(
    specs: list[dict[str, Any]],
    *,
    target_names_by_row: dict[str, list[str]] | None = None,
) -> dict[str, set[str]]:
    return _template_rows_by_kind(specs, test_kind="positive", target_names_by_row=target_names_by_row)


def _negative_template_rows(
    specs: list[dict[str, Any]],
    *,
    target_names_by_row: dict[str, list[str]] | None = None,
) -> dict[str, set[str]]:
    return _template_rows_by_kind(specs, test_kind="negative_control", target_names_by_row=target_names_by_row)


def _target_names_by_row_from_rows(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for row in rows:
        rid = _row_id(row)
        if not rid:
            continue
        for name in family_specs.target_names_from_row(row):
            if name not in out.setdefault(rid, []):
                out[rid].append(name)
    return out


def _iter_rows(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        return [row for row in obj if isinstance(row, dict)]
    if not isinstance(obj, dict):
        return []
    out: list[dict[str, Any]] = []
    for key in ("rows", "results", "row_results", "qualified_rows", "items", "corpus"):
        vals = obj.get(key)
        if isinstance(vals, list):
            out.extend(row for row in vals if isinstance(row, dict))
    for value in obj.values():
        if isinstance(value, dict) and any(k in value for k in ("row_id", "id", "target_id")):
            out.append(value)
    return out


def _normalize_row(row: dict[str, Any], *, source_path: str, source_kind: str) -> dict[str, Any]:
    rid = _row_id(row)
    rec = dict(row)
    rec["row_id"] = rid
    if not rec.get("source_file") and rec.get("sorried_file"):
        rec["source_file"] = rec.get("sorried_file")
    if "row_context_resolved_count" not in rec:
        rec["row_context_resolved_count"] = len(rec.get("row_context_ready_candidates") or [])
    if "candidate_count" not in rec:
        rec["candidate_count"] = len(rec.get("candidates") or [])
    rec.setdefault("benchmark_row_source_path", source_path)
    rec.setdefault("benchmark_row_source_kind", source_kind)
    target_resolution = _row_target_resolution(rec)
    rec["target_resolution_status"] = target_resolution.get("status")
    rec["target_resolution"] = target_resolution
    if target_resolution.get("theorem_name"):
        rec["target_theorem_name"] = target_resolution.get("theorem_name")
    return rec


def _rows_from_path(path: str | Path, *, source_kind: str) -> list[dict[str, Any]]:
    obj = _read_json(path)
    rows: list[dict[str, Any]] = []
    for row in _iter_rows(obj):
        rid = _row_id(row)
        if rid:
            rows.append(_normalize_row(row, source_path=str(path), source_kind=source_kind))
    return rows


def _expand_row_globs(patterns: list[str], *, max_matches: int) -> list[str]:
    paths: list[Path] = []
    for pattern in patterns:
        matches = sorted(Path().glob(pattern)) if not Path(pattern).is_absolute() else sorted(Path(pattern).parent.glob(Path(pattern).name))
        paths.extend(path for path in matches if path.is_file())
    paths = sorted(paths, key=lambda path: path.stat().st_mtime, reverse=True)[:max(0, int(max_matches))]
    seen: set[str] = set()
    out: list[str] = []
    for path_obj in paths:
        path = str(path_obj)
        if path in seen:
            continue
        seen.add(path)
        out.append(path)
    return out


def _merge_row_sources(primary_path: str, supplemental_paths: list[str], supplemental_globs: list[str], *, max_supplemental_glob_matches: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    source_counts: dict[str, int] = {}
    primary_rows = _rows_from_path(primary_path, source_kind="primary")
    for row in primary_rows:
        merged.setdefault(str(row["row_id"]), row)
    source_counts[primary_path] = len(primary_rows)

    expanded_supplemental = [
        *supplemental_paths,
        *_expand_row_globs(supplemental_globs, max_matches=max_supplemental_glob_matches),
    ]
    for path in expanded_supplemental:
        rows = _rows_from_path(path, source_kind="supplemental")
        source_counts[path] = len(rows)
        for row in rows:
            rid = str(row["row_id"])
            if rid not in merged:
                merged[rid] = row
                continue
            existing = merged[rid]
            existing_source = str(existing.get("source_file") or "")
            row_source = str(row.get("source_file") or row.get("sorried_file") or "")
            if (
                row_source
                and (not existing_source or (not Path(existing_source).exists() and Path(row_source).exists()))
            ):
                existing["source_file"] = row.get("source_file") or row.get("sorried_file")
                if row.get("sorried_file"):
                    existing["sorried_file"] = row.get("sorried_file")
            for key in ("source", "goal", "target_line", "target_theorem_name", "theorem_name"):
                if not existing.get(key) and row.get(key):
                    existing[key] = row.get(key)
            if int(row.get("row_context_resolved_count") or 0) > int(existing.get("row_context_resolved_count") or 0):
                existing["row_context_resolved_count"] = int(row.get("row_context_resolved_count") or 0)
            if existing.get("benchmark_row_source_kind") != "primary":
                existing["benchmark_row_source_path"] = row.get("benchmark_row_source_path")
    return list(merged.values()), {
        "primary_row_count": len(primary_rows),
        "supplemental_paths": expanded_supplemental,
        "source_counts": source_counts,
        "merged_row_count": len(merged),
    }


def _registry_index(registry: dict[str, Any]) -> tuple[dict[str, set[str]], dict[str, set[str]], dict[str, str]]:
    attempted_by_family: dict[str, set[str]] = {}
    ratified_by_family: dict[str, set[str]] = {}
    status_by_family: dict[str, str] = {}
    for fam in registry.get("families") or []:
        family = str(fam.get("family") or "")
        if not family:
            continue
        attempted_by_family[family] = {str(x) for x in (fam.get("rows_attempted") or []) if str(x)}
        ratified_by_family[family] = {str(x) for x in (fam.get("ratified_rows") or []) if str(x)}
        status_by_family[family] = str(fam.get("status") or "")
    return attempted_by_family, ratified_by_family, status_by_family


def _all_ratified_rows(ratified_by_family: dict[str, set[str]]) -> set[str]:
    out: set[str] = set()
    for rows in ratified_by_family.values():
        out.update(rows)
    return out


def _all_attempted_rows(attempted_by_family: dict[str, set[str]]) -> set[str]:
    out: set[str] = set()
    for rows in attempted_by_family.values():
        out.update(rows)
    return out


def _tier_rows(rows: list[dict[str, Any]], registry: dict[str, Any], *, limit: int, positive_template_rows: dict[str, set[str]] | None = None) -> dict[str, list[dict[str, Any]]]:
    attempted_by_family, ratified_by_family, status_by_family = _registry_index(registry)
    ratified_rows = _all_ratified_rows(ratified_by_family)
    attempted_rows = _all_attempted_rows(attempted_by_family)
    candidate_or_better_rows: set[str] = set()
    for family, status in status_by_family.items():
        if status in {"candidate_family", "validated_family"}:
            candidate_or_better_rows.update(attempted_by_family.get(family) or set())

    tiers: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        rid = _row_id(row)
        if not rid:
            continue
        rec = {
            "row_id": rid,
            "source_file": row.get("source_file"),
            "candidate_count": int(row.get("candidate_count") or len(row.get("candidates") or [])),
            "row_context_resolved_count": int(row.get("row_context_resolved_count") or len(row.get("row_context_ready_candidates") or [])),
            "status": row.get("status"),
            "benchmark_row_source_path": row.get("benchmark_row_source_path"),
            "benchmark_row_source_kind": row.get("benchmark_row_source_kind"),
            "target_resolution_status": row.get("target_resolution_status"),
            "target_theorem_name": row.get("target_theorem_name"),
        }
        if rid in ratified_rows:
            tier = "known_possible_controls"
        elif rid in (positive_template_rows or {}):
            tier = "family_spec_template_rows"
        elif rid in candidate_or_better_rows:
            tier = "repair_family_sibling_or_heldout"
        elif rid in attempted_rows:
            tier = "corrected_escape_route_rows"
        elif rec["row_context_resolved_count"] >= 3:
            tier = "target_context_ready_tractable"
        else:
            tier = "hard_open_or_gap_candidates"
        tiers[tier].append(rec)

    per_tier_cap = max(1, limit // max(1, len(ORDERED_TIERS)))
    out: dict[str, list[dict[str, Any]]] = {tier: [] for tier in ORDERED_TIERS}
    selected_total = 0
    for tier in ORDERED_TIERS:
        vals = tiers.get(tier, [])
        out[tier] = vals[:per_tier_cap]
        selected_total += len(out[tier])
    if selected_total < limit:
        seen = {r["row_id"] for vals in out.values() for r in vals}
        for tier in ORDERED_TIERS:
            for rec in tiers.get(tier, []):
                if selected_total >= limit:
                    break
                if rec["row_id"] in seen:
                    continue
                out[tier].append(rec)
                seen.add(rec["row_id"])
                selected_total += 1
            if selected_total >= limit:
                break
    return out


def _flatten_rows(tiers: dict[str, list[dict[str, Any]]]) -> list[str]:
    max_len = max((len(tiers.get(tier, [])) for tier in ORDERED_TIERS), default=0)
    out: list[str] = []
    seen: set[str] = set()
    for index in range(max_len):
        for tier in ORDERED_TIERS:
            vals = tiers.get(tier, [])
            if index >= len(vals):
                continue
            row_id = str(vals[index].get("row_id") or "")
            if row_id and row_id not in seen:
                seen.add(row_id)
                out.append(row_id)
    return out


def _row_support_diagnostics(rows: list[dict[str, Any]], selected: list[str], positive_rows: dict[str, set[str]], negative_rows: dict[str, set[str]], *, min_resolved: int) -> dict[str, Any]:
    by_id = {_row_id(row): row for row in rows if _row_id(row)}
    selected_recs = []
    for rid in selected:
        row = by_id.get(rid, {})
        source_file = str(row.get("source_file") or "")
        has_positive = rid in positive_rows
        has_negative = bool(negative_rows.get(rid))
        resolved = int(row.get("row_context_resolved_count") or 0)
        source_exists = bool(source_file and Path(source_file).exists())
        if has_positive and source_exists:
            support_class = "in_grid_positive_exists"
        elif has_positive:
            support_class = "requires_new_source"
        elif resolved >= min_resolved:
            support_class = "no_known_positive"
        elif source_file and not source_exists:
            support_class = "too_hard_or_malformed"
        else:
            support_class = "requires_new_template"
        selected_recs.append({
            "row_id": rid,
            "support_class": support_class,
            "families_with_positive_template": sorted(positive_rows.get(rid) or []),
            "families_with_negative_control": sorted(negative_rows.get(rid) or []),
            "has_positive_template": has_positive,
            "has_negative_control": has_negative,
            "row_context_resolved_count": resolved,
            "source_file": source_file,
            "source_file_exists": source_exists,
            "row_source_kind": row.get("benchmark_row_source_kind"),
            "row_source_path": row.get("benchmark_row_source_path"),
        })
    support_counts = defaultdict(int)
    for rec in selected_recs:
        support_counts[str(rec["support_class"])] += 1
    return {
        "selected_rows": selected_recs,
        "support_counts": dict(sorted(support_counts.items())),
        "template_row_total": len(positive_rows),
        "selected_template_rows": [rid for rid in selected if rid in positive_rows],
        "selected_template_rows_with_negative_controls": [rid for rid in selected if rid in positive_rows and rid in negative_rows],
    }


def _next_blocker(contract: dict[str, Any], registry: dict[str, Any], *, family_template_selected_count: int, min_family_template_rows: int) -> dict[str, Any]:
    readiness = contract.get("benchmark_readiness") or {}
    blockers = []
    if not readiness.get("passes_row_inventory_gate"):
        blockers.append("target_context_ready_rows")
    if not readiness.get("passes_family_inventory_gate"):
        blockers.append("candidate_or_better_family_inventory")
    if family_template_selected_count < min_family_template_rows:
        blockers.append("family_template_row_overlap")
    candidates = []
    for fam in registry.get("families") or []:
        if fam.get("status") in {"candidate_family", "validated_family_requires_true_holdout_check"}:
            candidates.append({
                "family": fam.get("family"),
                "status": fam.get("status"),
                "unique_ratified_rows": fam.get("unique_ratified_rows"),
                "next_required_evidence": fam.get("next_required_evidence"),
                "negative_control_pass_rate": fam.get("negative_control_pass_rate"),
            })
    candidates.sort(key=lambda x: (-int(x.get("unique_ratified_rows") or 0), str(x.get("family") or "")))
    return {
        "blockers": blockers,
        "next_family_validation_targets": candidates[:3],
        "family_template_selected_count": family_template_selected_count,
        "min_family_template_rows": min_family_template_rows,
        "benchmark_can_run_full": not blockers,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    registry = _read_json(args.registry) or {}
    supplemental_contexts = list(args.supplemental_row_context or [])
    supplemental_contexts.extend(_policy_list("evaluation_harness_supplemental_row_contexts", path=args.factory_policy))
    supplemental_globs = list(args.supplemental_row_glob or [])
    supplemental_globs.extend(_policy_list("evaluation_harness_supplemental_row_globs", path=args.factory_policy))
    rows, row_source_summary = _merge_row_sources(
        args.row_context,
        supplemental_contexts,
        supplemental_globs,
        max_supplemental_glob_matches=int(args.max_supplemental_glob_matches),
    )
    source_materialization = _materialize_row_sources(
        rows,
        out_dir=args.source_snapshot_dir,
        args=args,
    )
    specs = family_specs.load_specs(args.spec_dir)
    target_names_by_row = _target_names_by_row_from_rows(rows)
    positive_template_rows = _positive_template_rows(specs, target_names_by_row=target_names_by_row)
    negative_template_rows = _negative_template_rows(specs, target_names_by_row=target_names_by_row)
    target_reference_quarantines = [
        failure for failure in family_specs.validate_specs(specs, target_names_by_row=target_names_by_row)
        if str(failure.get("failure") or "") in {
            "positive_template_references_target_theorem",
            "negative_control_references_target_theorem",
        }
    ]
    target_unresolved_rows = [row for row in rows if str(row.get("target_resolution_status") or "") != "pass"]
    selectable_rows = rows if args.allow_unresolved_target_rows else [row for row in rows if str(row.get("target_resolution_status") or "") == "pass"]
    tiers = _tier_rows(selectable_rows, registry, limit=args.limit, positive_template_rows=positive_template_rows)
    selected = _flatten_rows(tiers)
    selected_set = set(selected)
    selected_rows = [row for row in rows if _row_id(row) in selected_set]
    selected_target_unresolved_rows = [
        row for row in selected_rows
        if str(row.get("target_resolution_status") or "") != "pass"
    ]
    if args.merged_row_context_out:
        Path(args.merged_row_context_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.merged_row_context_out).write_text(json.dumps({
            "schema": "leanmill-evaluation-harness-selected-row-context-v1",
            "primary_row_context": args.row_context,
            "row_source_summary": row_source_summary,
            "source_materialization": source_materialization,
            "rows": selected_rows,
        }, indent=2, sort_keys=True) + "\n")
    row_context_for_contract = args.merged_row_context_out or args.row_context
    contract = de_contract.build_contract(argparse.Namespace(
        rows=",".join(selected),
        row_context_filter=row_context_for_contract,
        repair_family_registry=args.registry,
        out=args.contract_out,
        limit=args.limit,
        max_tool_calls=args.max_tool_calls,
        wall_timeout_s=args.wall_timeout_s,
        per_tool_timeout_s=args.per_tool_timeout_s,
        gold_n_steps=args.gold_n_steps,
    ))
    family_template_selected_count = sum(1 for row_id in selected if row_id in positive_template_rows)
    diagnostics = {
        "schema": "leanmill-evaluation-harness-prep-diagnostics-v1",
        "row_source_summary": row_source_summary,
        "source_materialization": source_materialization,
        "target_resolution": {
            "status": "pass" if not target_unresolved_rows else "fail",
            "unresolved_count": len(target_unresolved_rows),
            "unresolved_rows": [{"row_id": _row_id(row), "source_file": row.get("source_file"), "target_resolution": row.get("target_resolution")} for row in target_unresolved_rows[:50]],
        },
        "selected_target_resolution": {
            "status": "pass" if not selected_target_unresolved_rows else "fail",
            "unresolved_count": len(selected_target_unresolved_rows),
            "unresolved_rows": [
                {"row_id": _row_id(row), "source_file": row.get("source_file"), "target_resolution": row.get("target_resolution")}
                for row in selected_target_unresolved_rows[:50]
            ],
        },
        "row_support": _row_support_diagnostics(
            rows,
            selected,
            positive_template_rows,
            negative_template_rows,
            min_resolved=int(args.min_row_context_resolved),
        ),
    }
    payload = {
        "schema": "leanmill-evaluation-harness-prep-v1",
        "primary_row_context": args.row_context,
        "row_context": row_context_for_contract,
        "registry": args.registry,
        "contract": args.contract_out,
        "diagnostics": args.diagnostics_out,
        "selected_row_count": len(selected),
        "selected_rows_order": selected,
        "tiers": tiers,
        "tier_counts": {tier: len(tiers.get(tier, [])) for tier in ORDERED_TIERS},
        "arms": [arm.get("arm") for arm in contract.get("arms") or []],
        "benchmark_readiness": contract.get("benchmark_readiness"),
        "benchmark_preflight": {
            "family_template_selected_count": family_template_selected_count,
            "min_family_template_rows": int(args.min_family_template_rows),
            "selected_template_rows": [row_id for row_id in selected if row_id in positive_template_rows],
            "selected_template_rows_with_negative_controls": [row_id for row_id in selected if row_id in positive_template_rows and row_id in negative_template_rows],
            "min_row_context_resolved": int(args.min_row_context_resolved),
            "target_aware_family_template_filter": {
                "target_context_row_count": len(target_names_by_row),
                "positive_template_row_count": len(positive_template_rows),
                "negative_template_row_count": len(negative_template_rows),
                "target_reference_quarantine_count": len(target_reference_quarantines),
                "target_reference_quarantine_examples": target_reference_quarantines[:12],
                "rationale": "family template rows are eligible for benchmark-prep only after the same target-name quarantine used by the proof-loop seeder and gate",
            },
            "row_source_summary": row_source_summary,
            "source_materialization": source_materialization,
            "selected_target_resolution_status": "pass" if not selected_target_unresolved_rows else "fail",
            "selected_target_unresolved_row_count": len(selected_target_unresolved_rows),
            "full_pool_target_resolution_status": "pass" if not target_unresolved_rows else "fail",
            "full_pool_target_unresolved_row_count": len(target_unresolved_rows),
            "target_unresolved_rows_excluded": [_row_id(row) for row in target_unresolved_rows[:50]] if not args.allow_unresolved_target_rows else [],
        },
        "next_blocker": _next_blocker(
            contract,
            registry,
            family_template_selected_count=family_template_selected_count,
            min_family_template_rows=int(args.min_family_template_rows),
        ),
    }
    if args.diagnostics_out:
        Path(args.diagnostics_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.diagnostics_out).write_text(json.dumps(diagnostics, indent=2, sort_keys=True) + "\n")
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if payload["next_blocker"]["blockers"] and not args.allow_not_ready:
        raise SystemExit("benchmark prep preflight failed: " + json.dumps(payload["next_blocker"], sort_keys=True))
    if args.md:
        Path(args.md).parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# LeanMill Evaluation Harness Prep",
            "",
            f"- selected rows: `{len(selected)}`",
            f"- contract: `{args.contract_out}`",
            f"- row_context: `{row_context_for_contract}`",
            f"- full benchmark ready: `{payload['next_blocker']['benchmark_can_run_full']}`",
            f"- blockers: `{', '.join(payload['next_blocker']['blockers']) or 'none'}`",
            f"- family_template_selected_count: `{family_template_selected_count}`",
            f"- diagnostics: `{args.diagnostics_out}`",
            "",
            "## Tier Counts",
            "",
        ]
        for tier in ORDERED_TIERS:
            lines.append(f"- `{tier}`: `{payload['tier_counts'].get(tier, 0)}`")
        lines.extend(["", "## Arms", ""])
        for arm in payload["arms"]:
            lines.append(f"- `{arm}`")
        lines.extend(["", "## Row Support", ""])
        for klass, count in diagnostics["row_support"]["support_counts"].items():
            lines.append(f"- `{klass}`: `{count}`")
        lines.extend(["", "## Next Family Validation Targets", ""])
        for rec in payload["next_blocker"]["next_family_validation_targets"]:
            lines.append(f"- `{rec['family']}` ratified_rows=`{rec['unique_ratified_rows']}` next=`{rec['next_required_evidence']}`")
        Path(args.md).write_text("\n".join(lines) + "\n")
    return payload


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="leanmill_benchmark_prep_") as td:
        root = Path(td)
        (root / "r1.lean").write_text("theorem r1 : True := by\n  trivial\n")
        (root / "r2.lean").write_text("theorem r2 : True := by\n  trivial\n")
        (root / "r3.lean").write_text("theorem r3 : True := by\n  trivial\n")
        (root / "bad.lean").write_text("theorem bad_alpha : True := by\n  trivial\n\ntheorem bad_beta : True := by\n  trivial\n")
        mathlib_root = root / "Mathlib"
        (mathlib_root / "Analysis").mkdir(parents=True)
        (mathlib_root / "Analysis" / "Demo.lean").write_text(
            "theorem supplemental_target : True := by\n  trivial\n\ntheorem after_target : True := by\n  trivial\n"
        )
        rows = {
            "rows": [
                {"row_id": "r1", "candidate_count": 3, "row_context_resolved_count": 3, "source_file": str(root / "r1.lean")},
                {"row_id": "r2", "candidate_count": 2, "row_context_resolved_count": 2, "source_file": str(root / "r2.lean")},
                {"row_id": "r3", "target_theorem_name": "r3", "candidate_count": 1, "row_context_resolved_count": 1, "source_file": str(root / "r3.lean")},
                {"row_id": "bad", "candidate_count": 1, "row_context_resolved_count": 1, "source_file": str(root / "bad.lean")},
                {"row_id": "mcb_missing", "candidate_count": 3, "row_context_resolved_count": 3, "source_file": str(root / "missing.lean")},
            ]
        }
        supplemental = {
            "rows": [
                {
                    "row_id": "mcb_missing",
                    "source_file": str(root / "missing.lean"),
                    "source": {"mathlib_name": "supplemental_target", "file": "Analysis/Demo.lean"},
                }
            ]
        }
        registry = {
            "status_counts": {"candidate_family": 1, "validated_family": 1},
            "families": [
                {"family": "fam", "status": "candidate_family", "rows_attempted": ["r2"], "ratified_rows": ["r2"], "unique_ratified_rows": 1},
                {"family": "vfam", "status": "validated_family", "rows_attempted": ["r1"], "ratified_rows": ["r1"], "unique_ratified_rows": 1},
            ],
        }
        row_path = root / "rows.json"
        supplemental_path = root / "supplemental.json"
        reg_path = root / "registry.json"
        spec_dir = root / "specs"
        spec_dir.mkdir()
        row_path.write_text(json.dumps(rows))
        supplemental_path.write_text(json.dumps(supplemental))
        reg_path.write_text(json.dumps(registry))
        (spec_dir / "leaked_template_family.yaml").write_text(
            "\n".join([
                "family: leaked_template_family",
                "version: 1",
                "status: seed_only",
                "credit:",
                "  source_credit_eligible: false",
                "  clean_solver_credit_eligible: false",
                "templates:",
                "  - id: leaked_positive",
                "    row_id: r3",
                "    test_kind: positive",
                "    expected_outcome: pass",
                "    backend: repl_file",
                "    timeout: 10",
                "    body: \"exact r3\"",
                "  - id: leaked_negative",
                "    row_id: r3",
                "    test_kind: negative_control",
                "    expected_outcome: fail",
                "    backend: repl_file",
                "    timeout: 10",
                "    body: \"trivial\"",
                "",
            ])
        )
        payload = build(argparse.Namespace(
            row_context=str(row_path),
            supplemental_row_context=[str(supplemental_path)],
            supplemental_row_glob=[],
            registry=str(reg_path),
            contract_out=str(root / "contract.json"),
            out=None,
            md=None,
            diagnostics_out=str(root / "diagnostics.json"),
            merged_row_context_out=str(root / "merged_rows.json"),
            factory_policy=str(root / "missing_policy.json"),
            spec_dir=str(spec_dir),
            min_family_template_rows=0,
            min_row_context_resolved=1,
            max_supplemental_glob_matches=20,
            source_snapshot_dir=str(root / "source_snapshots"),
            mathlib_root=str(mathlib_root),
            allow_not_ready=True,
            allow_unresolved_target_rows=False,
            limit=4,
            max_tool_calls=4,
            wall_timeout_s=60,
            per_tool_timeout_s=10,
            gold_n_steps=6,
        ))
        assert payload["selected_row_count"] == 4, payload
        assert payload["benchmark_preflight"]["full_pool_target_unresolved_row_count"] == 1, payload
        assert payload["benchmark_preflight"]["selected_target_unresolved_row_count"] == 0, payload
        assert "bad" not in payload["selected_rows_order"], payload
        assert "mcb_missing" in payload["selected_rows_order"], payload
        assert payload["tier_counts"]["known_possible_controls"] == 2, payload
        assert payload["tier_counts"].get("family_spec_template_rows") == 0, payload
        assert payload["benchmark_preflight"]["family_template_selected_count"] == 0, payload
        assert payload["benchmark_preflight"]["selected_template_rows"] == [], payload
        assert payload["benchmark_preflight"]["target_aware_family_template_filter"]["target_reference_quarantine_count"] == 1, payload
        assert payload["arms"][0] == "public_tool_static", payload
        assert Path(payload["row_context"]).exists(), payload
        merged = json.loads(Path(payload["row_context"]).read_text())
        materialized = [row for row in merged["rows"] if row["row_id"] == "mcb_missing"][0]
        assert Path(materialized["source_file"]).exists(), materialized
        assert materialized["target_resolution_status"] == "pass", materialized
        assert "sorry" in Path(materialized["source_file"]).read_text(), materialized
        assert payload["benchmark_preflight"]["source_materialization"]["counts"].get("materialized", 0) == 1, payload
    print("leanmill_benchmark_prep self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--row-context", default=DEFAULT_ROW_CONTEXT)
    ap.add_argument("--supplemental-row-context", action="append", default=[])
    ap.add_argument("--supplemental-row-glob", action="append", default=[])
    ap.add_argument("--registry", default=REPAIR_FAMILY_REGISTRY)
    ap.add_argument("--factory-policy", default=FACTORY_POLICY)
    ap.add_argument("--spec-dir", default=DEFAULT_SPEC_DIR)
    ap.add_argument("--min-family-template-rows", type=int, default=_policy_int("evaluation_harness_min_family_template_rows", 1))
    ap.add_argument("--min-row-context-resolved", type=int, default=_policy_int("evaluation_harness_min_row_context_resolved", 1))
    ap.add_argument("--max-supplemental-glob-matches", type=int, default=_policy_int("evaluation_harness_max_supplemental_glob_matches", 120))
    ap.add_argument("--contract-out", default=DEFAULT_CONTRACT)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--md", default=DEFAULT_MD)
    ap.add_argument("--diagnostics-out", default=DEFAULT_DIAGNOSTICS)
    ap.add_argument("--merged-row-context-out", default=DEFAULT_MERGED_ROW_CONTEXT)
    ap.add_argument("--source-snapshot-dir", default=DEFAULT_SOURCE_SNAPSHOT_DIR)
    ap.add_argument("--mathlib-root", default="")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--max-tool-calls", type=int, default=12)
    ap.add_argument("--wall-timeout-s", type=int, default=180)
    ap.add_argument("--per-tool-timeout-s", type=int, default=30)
    ap.add_argument("--gold-n-steps", type=int, default=6)
    ap.add_argument("--allow-not-ready", action="store_true")
    ap.add_argument("--allow-unresolved-target-rows", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    payload = build(args)
    print(json.dumps({
        "out": args.out,
        "contract": args.contract_out,
        "diagnostics": args.diagnostics_out,
        "row_context": payload["row_context"],
        "selected_row_count": payload["selected_row_count"],
        "full_benchmark_ready": payload["next_blocker"]["benchmark_can_run_full"],
        "blockers": payload["next_blocker"]["blockers"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
