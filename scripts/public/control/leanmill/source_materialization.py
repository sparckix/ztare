#!/usr/bin/env python3
"""Materialize LeanMill row source snapshots from Mathlib metadata.

This is infrastructure for executable probes and benchmarks only. A materialized
snapshot gives downstream tools a stable file path and target declaration; it
does not create proof, benchmark, source, or C-supply credit.
"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


THEOREM_NAME_RE = re.compile(
    r"(?:^|\n)\s*(?:@[^\n]*\n\s*)*"
    r"(?:public\s+|private\s+|protected\s+|noncomputable\s+|unsafe\s+)*"
    r"(?:theorem|lemma)\s+([^\s:]+)"
)
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
MATHLIB_EXISTING_DECL_MATERIALIZATION = "mathlib_existing_decl_snapshot"


def row_id(row: dict[str, Any]) -> str:
    return str(row.get("row_id") or row.get("id") or row.get("target_id") or "")


def _append_unique(values: list[str], value: Any) -> None:
    item = str(value or "").strip()
    if item and item not in values:
        values.append(item)


def row_theorem_name_candidates(row: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    source = row.get("source") if isinstance(row.get("source"), dict) else {}
    for key in (
        "mathlib_name",
        "target_theorem_name",
        "theorem_name",
        "decl_name",
        "declaration_name",
        "target_name",
        "source_declaration",
    ):
        _append_unique(candidates, row.get(key))
        _append_unique(candidates, source.get(key))
    match = THEOREM_NAME_RE.search(str(row.get("goal") or row.get("source_hinge") or ""))
    if match:
        _append_unique(candidates, match.group(1))
    rid = row_id(row)
    match = re.match(r"^[A-Z][A-Z0-9]*_\d+_([A-Za-z_][A-Za-z0-9_'.]*)$", rid)
    _append_unique(candidates, match.group(1) if match else rid)
    return candidates


def row_has_mathlib_source_metadata(row: dict[str, Any]) -> bool:
    source = row.get("source") if isinstance(row.get("source"), dict) else {}
    source_file_rel = str(source.get("file") or row.get("mathlib_file") or "").strip()
    return bool(source_file_rel and row_theorem_name_candidates(row))


def slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in value).strip("_") or "row"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _mathlib_root(configured: str | Path | None = None) -> Path | None:
    configured_text = str(configured or "")
    candidates = [Path(configured_text)] if configured_text else []
    candidates.extend([
        Path("ztare_proofs/.lake/packages/mathlib/Mathlib"),
        Path(".lake/packages/mathlib/Mathlib"),
    ])
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def _resolve_mathlib_source_path(root: Path, source_file_rel: str) -> Path:
    rel = source_file_rel.strip()
    candidates = [root / rel]
    if rel.startswith("Mathlib/"):
        candidates.append(root / rel.removeprefix("Mathlib/"))
    if root.name != "Mathlib":
        candidates.append(root / "Mathlib" / rel)
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return candidates[0]


def find_target_start(text: str, theorem_name: str) -> int:
    if not theorem_name:
        return -1
    pattern = re.compile(DECL_RE_TEMPLATE.format(name=re.escape(theorem_name)))
    match = pattern.search(text)
    return -1 if not match else match.start(0) + (1 if match.group(1) else 0)


def _line_number_at(text: str, offset: int) -> int:
    if offset < 0:
        return 0
    return text.count("\n", 0, min(offset, len(text))) + 1


def resolve_theorem_name(text: str, preferred: str) -> dict[str, Any]:
    if find_target_start(text, preferred) >= 0:
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


def row_target_resolution(row: dict[str, Any]) -> dict[str, Any]:
    rid = row_id(row)
    source_file = Path(str(row.get("source_file") or row.get("sorried_file") or ""))
    if not source_file.exists() or not source_file.is_file():
        return {"status": "fail", "row_id": rid, "reason": "missing_source_file", "source_file": str(source_file)}
    text = source_file.read_text(errors="ignore")
    attempts: list[dict[str, Any]] = []
    for candidate in row_theorem_name_candidates(row):
        resolved = resolve_theorem_name(text, candidate)
        attempts.append(resolved)
        theorem_name = str(resolved.get("theorem_name") or "")
        if theorem_name:
            return {
                "status": "pass",
                "row_id": rid,
                "theorem_name": theorem_name,
                "target_line": _line_number_at(text, find_target_start(text, theorem_name)),
                "resolution": resolved,
                "source_file": str(source_file),
            }
    return {
        "status": "fail",
        "row_id": rid,
        "reason": "target_theorem_not_resolved",
        "resolution_attempts": attempts[-3:],
        "source_file": str(source_file),
    }


def replace_decl_body_with_sorry(src: str, theorem_name: str) -> dict[str, Any]:
    start = find_target_start(src, theorem_name)
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
        "target_line": _line_number_at(src, start),
        "theorem_name": theorem_name,
        "original_block_sha256": sha256_text(block),
    }


def materialize_source_from_mathlib(
    row: dict[str, Any],
    *,
    out_dir: str | Path,
    mathlib_root: str | Path | None = None,
) -> dict[str, Any]:
    source = row.get("source") if isinstance(row.get("source"), dict) else {}
    source_file_rel = str(source.get("file") or row.get("mathlib_file") or "")
    theorem_name = ""
    for candidate in row_theorem_name_candidates(row):
        if candidate:
            theorem_name = candidate
            break
    if not source_file_rel or not theorem_name:
        return {"status": "skip", "reason": "missing_mathlib_source_metadata"}
    root = _mathlib_root(mathlib_root)
    if root is None:
        return {"status": "fail", "reason": "mathlib_root_missing"}
    source_path = _resolve_mathlib_source_path(root, source_file_rel)
    if not source_path.exists() or not source_path.is_file():
        return {"status": "fail", "reason": "mathlib_file_missing", "mathlib_file": str(source_path)}
    src = source_path.read_text(errors="ignore")
    resolved = resolve_theorem_name(src, theorem_name)
    resolved_name = str(resolved.get("theorem_name") or "")
    if not resolved_name:
        return {
            "status": "fail",
            "reason": "decl_not_resolved",
            "theorem_name": theorem_name,
            "mathlib_file": str(source_path),
            "resolution": resolved,
        }
    replaced = replace_decl_body_with_sorry(src, resolved_name)
    if replaced.get("status") != "pass":
        return {**replaced, "mathlib_file": str(source_path)}
    target = Path(out_dir) / f"{slug(row_id(row)) or slug(resolved_name)}.lean"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(str(replaced["text"]), encoding="utf-8")
    return {
        "status": "materialized",
        "materialization_source": MATHLIB_EXISTING_DECL_MATERIALIZATION,
        "existing_mathlib_target": True,
        "strict_c_credit_disqualified_reason": "existing_mathlib_target_snapshot",
        "source_file": str(target),
        "sorried_file": str(target),
        "target_line": replaced.get("target_line"),
        "target_theorem_name": resolved_name,
        "mathlib_file": str(source_path),
        "mathlib_source_rel": source_file_rel,
        "source_sha256": sha256_text(str(replaced["text"])),
        "original_block_sha256": replaced.get("original_block_sha256"),
        "resolution": resolved,
    }


def _inline_goal_skeleton_text(row: dict[str, Any]) -> dict[str, Any]:
    raw = str(row.get("goal") or row.get("source_hinge") or "").strip()
    if not raw:
        return {"status": "skip", "reason": "missing_inline_goal"}
    if not THEOREM_NAME_RE.search(raw):
        return {"status": "skip", "reason": "inline_goal_not_theorem"}
    if "⊢" in raw:
        return {"status": "skip", "reason": "inline_goal_is_tactic_state"}
    if ":= by" in raw:
        prefix = raw.split(":= by", 1)[0].rstrip()
        text = f"import Mathlib\n\n{prefix} := by\n  sorry\n"
    elif ":=" in raw:
        prefix = raw.split(":=", 1)[0].rstrip()
        text = f"import Mathlib\n\n{prefix} := by\n  sorry\n"
    else:
        text = f"import Mathlib\n\n{raw.rstrip()} := by\n  sorry\n"
    match = THEOREM_NAME_RE.search(text)
    theorem_name = match.group(1) if match else ""
    if not theorem_name:
        return {"status": "skip", "reason": "inline_goal_theorem_name_unresolved"}
    return {
        "status": "pass",
        "text": text,
        "target_theorem_name": theorem_name,
    }


def materialize_source_from_inline_goal(
    row: dict[str, Any],
    *,
    out_dir: str | Path,
) -> dict[str, Any]:
    skeleton = _inline_goal_skeleton_text(row)
    if skeleton.get("status") != "pass":
        return skeleton
    target = Path(out_dir) / f"{slug(row_id(row)) or slug(str(skeleton.get('target_theorem_name') or 'row'))}.lean"
    target.parent.mkdir(parents=True, exist_ok=True)
    text = str(skeleton["text"])
    target.write_text(text, encoding="utf-8")
    return {
        "status": "materialized",
        "materialization_source": "inline_goal_skeleton",
        "source_file": str(target),
        "sorried_file": str(target),
        "target_line": 3,
        "target_theorem_name": str(skeleton.get("target_theorem_name") or ""),
        "source_sha256": sha256_text(text),
        "credit_boundary": "inline goal skeleton only; no proof, benchmark, source, or C-supply credit",
    }


def snapshot_path_for_row(row: dict[str, Any], *, out_dir: str | Path) -> Path:
    rid = row_id(row)
    name = rid
    if not name:
        for candidate in row_theorem_name_candidates(row):
            if candidate:
                name = candidate
                break
    return Path(out_dir) / f"{slug(name)}.lean"


def materialize_row_sources(
    rows: list[dict[str, Any]],
    *,
    out_dir: str | Path,
    mathlib_root: str | Path | None = None,
) -> dict[str, Any]:
    receipts: list[dict[str, Any]] = []
    counts: dict[str, int] = defaultdict(int)
    if not out_dir:
        return {"status": "disabled", "receipts": [], "counts": {}}
    for row in rows:
        rid = row_id(row)
        source_file = str(row.get("source_file") or row.get("sorried_file") or "")
        if source_file and Path(source_file).exists() and Path(source_file).is_file():
            receipt = {"status": "already_present", "row_id": rid, "source_file": source_file}
            if row_has_mathlib_source_metadata(row):
                receipt.update({
                    "materialization_source": MATHLIB_EXISTING_DECL_MATERIALIZATION,
                    "existing_mathlib_target": True,
                    "strict_c_credit_disqualified_reason": "existing_mathlib_target_snapshot",
                })
                row["existing_mathlib_target"] = True
                row["strict_c_credit_disqualified_reason"] = "existing_mathlib_target_snapshot"
        else:
            snapshot = snapshot_path_for_row(row, out_dir=out_dir)
            if snapshot.exists() and snapshot.is_file():
                row["source_file"] = str(snapshot)
                row["sorried_file"] = str(snapshot)
                resolution = row_target_resolution(row)
                if resolution.get("status") == "pass":
                    row["target_line"] = int(resolution.get("target_line") or row.get("target_line") or 0)
                    row["target_theorem_name"] = str(resolution.get("theorem_name") or row.get("target_theorem_name") or "")
                    receipt = {
                        "status": "already_present",
                        "row_id": rid,
                        "source_file": str(snapshot),
                        "reason": "deterministic_row_id_snapshot_exists",
                    }
                    if row_has_mathlib_source_metadata(row):
                        receipt.update({
                            "materialization_source": MATHLIB_EXISTING_DECL_MATERIALIZATION,
                            "existing_mathlib_target": True,
                            "strict_c_credit_disqualified_reason": "existing_mathlib_target_snapshot",
                        })
                        row["existing_mathlib_target"] = True
                        row["strict_c_credit_disqualified_reason"] = "existing_mathlib_target_snapshot"
                else:
                    receipt = materialize_source_from_mathlib(row, out_dir=out_dir, mathlib_root=mathlib_root)
            else:
                receipt = materialize_source_from_mathlib(row, out_dir=out_dir, mathlib_root=mathlib_root)
                if str(receipt.get("status") or "") in {"skip", "fail"} and str(receipt.get("reason") or "") in {
                    "missing_mathlib_source_metadata",
                    "mathlib_root_missing",
                    "mathlib_file_missing",
                    "decl_not_resolved",
                    "decl_not_found",
                }:
                    receipt = materialize_source_from_inline_goal(row, out_dir=out_dir)
            receipt["row_id"] = rid
            if receipt.get("status") == "materialized":
                row["source_file"] = receipt["source_file"]
                row["sorried_file"] = receipt["sorried_file"]
                row["target_line"] = int(receipt.get("target_line") or row.get("target_line") or 0)
                row["target_theorem_name"] = str(receipt.get("target_theorem_name") or row.get("target_theorem_name") or "")
                row["source_materialization"] = receipt
                if receipt.get("existing_mathlib_target"):
                    row["existing_mathlib_target"] = True
                    row["strict_c_credit_disqualified_reason"] = str(
                        receipt.get("strict_c_credit_disqualified_reason") or "existing_mathlib_target_snapshot"
                    )
        counts[str(receipt.get("status") or "unknown")] += 1
        receipts.append(receipt)
        row["target_resolution"] = row_target_resolution(row)
        row["target_resolution_status"] = row["target_resolution"].get("status")
        if row["target_resolution"].get("theorem_name"):
            row["target_theorem_name"] = row["target_resolution"].get("theorem_name")
    return {
        "status": "pass" if counts.get("fail", 0) == 0 else "partial",
        "out_dir": str(out_dir),
        "counts": dict(sorted(counts.items())),
        "failure_count": counts.get("fail", 0),
        "receipts": receipts[:120],
        "credit_boundary": "source materialization only; no proof, benchmark, source, or C-supply credit",
    }
