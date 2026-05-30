#!/usr/bin/env python3
"""Run a bounded LeanMill four-arm Evaluation Harness.

This runner consumes the frozen Evaluation Harness prep/contract artifacts. It
does not train, call LLMs, or update the repair registry. Each row/arm verdict
is appended to JSONL immediately, so interrupted runs can resume without
losing completed work.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import leanmill_family_specs as family_specs
from leanmill_factory_config import read_policy
from leanmill_paths import DATA_DIR, FACTORY_POLICY


DEFAULT_PREP = f"{DATA_DIR}/evaluation_harness_prep.json"
DEFAULT_CONTRACT = f"{DATA_DIR}/evaluation_harness_contract.json"
DEFAULT_SPEC_DIR = family_specs.DEFAULT_SPEC_DIR
DEFAULT_OUT = f"{DATA_DIR}/evaluation_harness_run.json"
DEFAULT_MD = f"{DATA_DIR}/evaluation_harness_run.md"
DEFAULT_CHECKPOINT = f"{DATA_DIR}/evaluation_harness_run.jsonl"
DEFAULT_ROOT = "/tmp/rung1/leanmill_evaluation_harness"
DEFAULT_LOCK = "/tmp/rung1/leanmill_heavy_lean.lock"

TOP_LEVEL_DECL_RE = re.compile(
    r"^(?:@[^\n]*\n)*"
    r"(?:public\s+|private\s+|protected\s+|noncomputable\s+|unsafe\s+|abbrev\s+)*"
    r"(?:theorem|lemma|def|abbrev|instance|structure|inductive|class)\s+",
    re.MULTILINE,
)
THEOREM_NAME_RE = re.compile(r"(?:^|\n)\s*(?:@[^\n]*\n\s*)*(?:public\s+|private\s+|protected\s+|noncomputable\s+|unsafe\s+)*\s*(?:theorem|lemma)\s+([^\s:]+)")
POSITIVE_SIGNAL_EXITS = {
    "ratified_closure",
    "governed_tool_tactic_closure_candidate",
    "raw_closure_candidate",
    "exact_gap",
    "valid_falsifier",
}
TARGET_REFERENCE_TEMPLATE_FAILURES = {
    "positive_template_references_target_theorem",
    "negative_control_references_target_theorem",
}


def _policy_operations(path: str | Path = FACTORY_POLICY) -> dict[str, Any]:
    policy = read_policy(path)
    ops = policy.get("operations") if isinstance(policy, dict) else {}
    return ops if isinstance(ops, dict) else {}


def _policy_int(key: str, fallback: int, *, path: str | Path = FACTORY_POLICY) -> int:
    try:
        return int(_policy_operations(path).get(key, fallback))
    except (TypeError, ValueError):
        return fallback


def _policy_str(key: str, fallback: str, *, path: str | Path = FACTORY_POLICY) -> str:
    value = _policy_operations(path).get(key, fallback)
    text = str(value or "").strip()
    return text or fallback


def _policy_dict(key: str, *, path: str | Path = FACTORY_POLICY) -> dict[str, Any]:
    value = _policy_operations(path).get(key, {})
    return value if isinstance(value, dict) else {}


def _sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    p = Path(path)
    if not p.exists() or not p.is_file():
        return ""
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _contract_canonical_sha256(contract_obj: dict[str, Any]) -> str:
    obj = dict(contract_obj)
    obj.pop("contract_sha256", None)
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _verify_contract_sha256(contract_path: str | Path, contract_obj: dict[str, Any]) -> dict[str, Any]:
    """Verify the pinned canonical contract SHA.

    The contract builder hashes the canonical JSON object before adding the
    ``contract_sha256`` field. Recompute that same hash here; hashing the whole
    file would make a correctly pinned contract appear stale.
    """
    pinned = str(contract_obj.get("contract_sha256") or "")
    file_sha = _sha256_file(contract_path)
    canonical_sha = _contract_canonical_sha256(contract_obj)
    if not pinned:
        return {
            "status": "skipped",
            "reason": "no contract_sha256 pin in contract",
            "file_sha256": file_sha,
            "canonical_sha256": canonical_sha,
        }
    if not file_sha:
        return {
            "status": "fail",
            "reason": "contract file unreadable",
            "pinned_sha256": pinned,
            "file_sha256": "",
            "canonical_sha256": canonical_sha,
        }
    if canonical_sha != pinned:
        return {
            "status": "fail",
            "reason": "contract canonical SHA256 drift",
            "pinned_sha256": pinned,
            "file_sha256": file_sha,
            "canonical_sha256": canonical_sha,
        }
    return {
        "status": "pass",
        "pinned_sha256": pinned,
        "file_sha256": file_sha,
        "canonical_sha256": canonical_sha,
    }


def _verify_tool_universe(contract_obj: dict[str, Any]) -> dict[str, Any]:
    """Verify every arm's ``route`` tactic is in the contract's ``tool_universe``.

    Pre-registered hard failure #4 (``adaptive_arm_uses_tool_outside_tool_substrate_catalog``).
    """
    universe = contract_obj.get("tool_universe") or []
    allowed = {str(t.get("tool_id") or "") for t in universe if isinstance(t, dict)}
    allowed.discard("")
    violations: list[dict[str, Any]] = []
    for arm in contract_obj.get("arms") or []:
        if not isinstance(arm, dict):
            continue
        arm_id = str(arm.get("arm") or "")
        for step in arm.get("route") or []:
            if not isinstance(step, dict):
                continue
            tool_id = str(step.get("tool_id") or "")
            if tool_id and tool_id not in allowed:
                violations.append({"arm": arm_id, "tool_id": tool_id})
    return {
        "status": "pass" if not violations else "fail",
        "allowed_tool_ids": sorted(allowed),
        "violations": violations,
    }


def _capture_toolchain_versions(spec_dir: str | Path) -> dict[str, Any]:
    """Capture Lean toolchain pin and best-effort Mathlib commit at run start.

    Recorded in the run receipt so any published benchmark can be reproduced
    against the exact substrate that produced it.
    """
    info: dict[str, Any] = {}
    # Lean toolchain pin file
    for candidate in ("ztare_proofs/lean-toolchain", "lean-toolchain"):
        p = Path(candidate)
        if p.exists() and p.is_file():
            info["lean_toolchain_path"] = str(p)
            info["lean_toolchain"] = p.read_text(errors="ignore").strip()
            break
    # `lean --version`, if available; never fatal
    try:
        proc = subprocess.run(["lean", "--version"], capture_output=True, text=True, timeout=5)
        info["lean_version"] = (proc.stdout or proc.stderr or "").strip().splitlines()[:3]
    except (OSError, subprocess.SubprocessError):
        info["lean_version"] = None
    # Mathlib commit (best-effort)
    mathlib_candidates = (
        "ztare_proofs/.lake/packages/mathlib",
        ".lake/packages/mathlib",
    )
    for cand in mathlib_candidates:
        gp = Path(cand) / ".git"
        if gp.exists():
            try:
                proc = subprocess.run(
                    ["git", "-C", cand, "rev-parse", "HEAD"],
                    capture_output=True, text=True, timeout=5,
                )
                info["mathlib_commit"] = (proc.stdout or "").strip()
                info["mathlib_path"] = cand
            except (OSError, subprocess.SubprocessError):
                pass
            break
    # spec_dir snapshot (per-file SHA), only if dir is small (<= 200 files)
    try:
        sp = Path(spec_dir)
        if sp.exists() and sp.is_dir():
            files = sorted(sp.glob("*.yaml"))
            if 0 < len(files) <= 200:
                info["spec_dir"] = str(sp)
                info["spec_files"] = [
                    {"name": f.name, "sha256": _sha256_file(f)}
                    for f in files
                ]
    except OSError:
        pass
    return info


def _snapshot_repair_families(spec_dir: str | Path, snapshot_root: str | Path, run_id: str) -> dict[str, Any]:
    """Air-gap the repair_families dir against mid-run edits by the live mill.

    Copies the dir to a read-only snapshot under ``snapshot_root``, returns a
    receipt with the snapshot path and per-file SHAs. Callers should then
    load specs from the snapshot path instead of the live dir.
    """
    src = Path(spec_dir)
    if not src.exists() or not src.is_dir():
        return {"status": "fail", "reason": "spec_dir missing", "spec_dir": str(src)}
    dst = Path(snapshot_root) / f"repair_families_{run_id}"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    files: list[dict[str, Any]] = []
    for f in sorted(dst.glob("*.yaml")):
        files.append({"name": f.name, "sha256": _sha256_file(f), "size_bytes": f.stat().st_size})
        # Best-effort read-only on the file. POSIX-only; ignore failures.
        try:
            os.chmod(f, 0o444)
        except OSError:
            pass
    return {"status": "ok", "snapshot_dir": str(dst), "files": files, "file_count": len(files)}


def _read_json(path: str | Path) -> Any:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return None


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value).strip("_") or "item"


def _iter_row_context_rows(obj: Any) -> list[dict[str, Any]]:
    if not isinstance(obj, dict):
        return []
    out: dict[str, dict[str, Any]] = {}
    for key in ("rows", "results", "row_results", "qualified_rows"):
        vals = obj.get(key)
        if not isinstance(vals, list):
            continue
        for row in vals:
            if not isinstance(row, dict):
                continue
            row_id = str(row.get("row_id") or row.get("id") or row.get("target_id") or "")
            if row_id:
                out.setdefault(row_id, row)
    for value in obj.values():
        if isinstance(value, dict):
            row_id = str(value.get("row_id") or value.get("id") or value.get("target_id") or "")
            if row_id:
                out.setdefault(row_id, value)
    return list(out.values())


def _selected_rows(prep: dict[str, Any], row_context: dict[str, Any], *, limit: int) -> list[dict[str, Any]]:
    effective_limit = max(0, int(limit or 0))
    by_id = {
        str(row.get("row_id") or row.get("id") or row.get("target_id")): row
        for row in _iter_row_context_rows(row_context)
    }
    tier_rec_by_id: dict[str, tuple[str, dict[str, Any]]] = {}
    for tier, vals in (prep.get("tiers") or {}).items():
        if not isinstance(vals, list):
            continue
        for rec in vals:
            if isinstance(rec, dict) and str(rec.get("row_id") or ""):
                tier_rec_by_id[str(rec.get("row_id"))] = (str(tier), rec)
    ordered = [str(x) for x in (prep.get("selected_rows_order") or []) if str(x)]
    if not ordered:
        ordered = [row_id for row_id, _ in tier_rec_by_id.items()]
    rows: list[dict[str, Any]] = []
    for row_id in ordered:
        if row_id not in tier_rec_by_id and row_id not in by_id:
            continue
        tier, rec = tier_rec_by_id.get(row_id, ("", {"row_id": row_id}))
        merged = {**by_id.get(row_id, {}), **rec, "tier": tier}
        rows.append(merged)
        if effective_limit and len(rows) >= effective_limit:
            return rows
    return rows


def _target_names_by_row_from_rows(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for row in rows:
        row_id = str(row.get("row_id") or row.get("id") or row.get("target_id") or "")
        if not row_id:
            continue
        for name in family_specs.target_names_from_row(row):
            if name not in out.setdefault(row_id, []):
                out[row_id].append(name)
    return out


def _append_unique(values: list[str], value: Any) -> None:
    text = str(value or "").strip()
    if text and text not in values:
        values.append(text)


def _row_theorem_name_candidates(row: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    source = row.get("source") if isinstance(row.get("source"), dict) else {}
    for key in ("mathlib_name", "theorem_name", "decl_name", "declaration_name", "target_name"):
        _append_unique(candidates, row.get(key))
        _append_unique(candidates, source.get(key))
    goal = str(row.get("goal") or "")
    m = THEOREM_NAME_RE.search(goal)
    if m:
        _append_unique(candidates, m.group(1))
    row_id = str(row.get("row_id") or "")
    parts = row_id.split("_", 2)
    _append_unique(candidates, parts[2] if len(parts) >= 3 else row_id)
    return candidates


def _theorem_name(row: dict[str, Any]) -> str:
    candidates = _row_theorem_name_candidates(row)
    return candidates[0] if candidates else ""


def _find_target_start(text: str, theorem_name: str) -> int:
    # Lean declaration names are not regex "word" tokens: Mathlib names can
    # contain apostrophes, dots, unicode, and quoted identifiers. Match the
    # declaration token and require the next character to be whitespace or the
    # type colon instead of using \b.
    pattern = re.compile(
        rf"(^|\n)\s*(?:@[^\n]*\n\s*)*"
        rf"(?:public\s+|private\s+|protected\s+|noncomputable\s+|unsafe\s+)*"
        rf"(?:theorem|lemma)\s+{re.escape(theorem_name)}(?=\s|:)"
    )
    match = pattern.search(text)
    if not match:
        return -1
    return match.start(0) + (1 if match.group(1) else 0)


def _line_number_at(text: str, offset: int) -> int:
    if offset < 0:
        return 0
    return text.count("\n", 0, min(offset, len(text))) + 1


def _target_line(row: dict[str, Any]) -> int:
    for key in ("target_line", "line", "start_line"):
        try:
            value = int(row.get(key) or 0)
        except (TypeError, ValueError):
            value = 0
        if value > 0:
            return value
    source = row.get("source") if isinstance(row.get("source"), dict) else {}
    try:
        return int(source.get("target_line") or source.get("line") or 0)
    except (TypeError, ValueError):
        return 0


def _resolve_by_target_line(text: str, names: list[str], preferred: str, target_line: int) -> dict[str, Any]:
    if target_line <= 0 or not names:
        return {"status": "no_target_line_resolution", "theorem_name": ""}
    located = []
    for name in names:
        start = _find_target_start(text, name)
        if start >= 0:
            line = _line_number_at(text, start)
            located.append((abs(line - target_line), line > target_line, line, name))
    if not located:
        return {"status": "target_line_no_located_decls", "theorem_name": "", "preferred": preferred}
    located.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
    _distance, _after, line, name = located[0]
    return {
        "status": "target_line_nearest",
        "theorem_name": name,
        "preferred": preferred,
        "target_line": target_line,
        "resolved_line": line,
        "candidates": [item[3] for item in located[:12]],
    }


def _resolve_theorem_name(text: str, preferred: str, target_line: int = 0) -> dict[str, Any]:
    if _find_target_start(text, preferred) >= 0:
        return {"status": "exact", "theorem_name": preferred}
    stem = preferred.rstrip("_")
    names = [m.group(1) for m in THEOREM_NAME_RE.finditer(text)]
    prefix_matches = [name for name in names if stem and name.startswith(stem)]
    if len(prefix_matches) == 1:
        return {"status": "prefix_unique", "theorem_name": prefix_matches[0], "preferred": preferred}
    if prefix_matches:
        line_resolution = _resolve_by_target_line(text, prefix_matches, preferred, target_line)
        if line_resolution.get("theorem_name"):
            return line_resolution
        return {
            "status": "ambiguous_prefix",
            "theorem_name": "",
            "preferred": preferred,
            "target_line": target_line or None,
            "candidates": prefix_matches[:12],
        }
    if len(names) == 1:
        return {"status": "single_theorem_in_source", "theorem_name": names[0], "preferred": preferred}
    line_resolution = _resolve_by_target_line(text, names, preferred, target_line)
    if line_resolution.get("theorem_name"):
        return line_resolution
    return {"status": "not_found", "theorem_name": "", "preferred": preferred, "target_line": target_line or None, "candidates": names[:12]}


def _find_body_start(text: str, theorem_start: int) -> int:
    idx = text.find(":= by", theorem_start)
    return idx


def _build_candidate_file(row: dict[str, Any], body: str, out_path: Path) -> dict[str, Any]:
    source_file = Path(str(row.get("source_file") or ""))
    preferred_theorem_name = _theorem_name(row)
    if not source_file.exists():
        return {"status": "fail", "reason": "missing_source_file", "source_file": str(source_file)}
    text = source_file.read_text(errors="ignore")
    target_line = _target_line(row)
    resolution_attempts: list[dict[str, Any]] = []
    resolved: dict[str, Any] = {}
    theorem_name = ""
    for candidate_name in _row_theorem_name_candidates(row):
        attempt = _resolve_theorem_name(text, candidate_name, target_line)
        resolution_attempts.append(attempt)
        theorem_name = str(attempt.get("theorem_name") or "")
        if theorem_name:
            resolved = attempt
            break
    if not theorem_name:
        resolved = resolution_attempts[-1] if resolution_attempts else {"status": "not_found", "theorem_name": ""}
        return {
            "status": "fail",
            "reason": "target_theorem_not_found",
            "theorem_name": preferred_theorem_name,
            "resolution": resolved,
            "resolution_attempts": resolution_attempts,
        }
    theorem_start = _find_target_start(text, theorem_name)
    if theorem_start < 0:
        return {"status": "fail", "reason": "target_theorem_not_found", "theorem_name": preferred_theorem_name, "resolution": resolved}
    body_start = _find_body_start(text, theorem_start)
    if body_start < 0:
        return {"status": "fail", "reason": "target_theorem_body_marker_not_found", "theorem_name": theorem_name}
    prefix = text[:body_start]
    candidate = prefix.rstrip() + " := by\n"
    for line in body.splitlines() or ["skip"]:
        candidate += f"  {line.rstrip()}\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(candidate, encoding="utf-8")
    return {"status": "pass", "theorem_name": theorem_name, "preferred_theorem_name": preferred_theorem_name, "resolution": resolved, "source_file": str(source_file)}


def _lean_project_root() -> Path:
    configured = os.environ.get("ZTARE_LEAN_PROJECT_ROOT")
    candidates = [Path(configured)] if configured else []
    candidates.extend([Path("ztare_proofs"), Path(".")])
    for candidate in candidates:
        if candidate and (candidate / "lean-toolchain").exists() and (candidate / "lakefile.toml").exists():
            return candidate
    return Path(".")


def _lean_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    configured = str(env.get("ZTARE_LEAN_PATH_PREFIXES") or env.get("ZTARE_VPS_REMOTE_PATH_PREFIXES") or "")
    prefixes = [p for p in configured.split(":") if p]
    prefixes.extend([
        str(Path.home() / ".elan" / "bin"),
        str(Path.home() / ".local" / "bin"),
        "/usr/local/bin",
        "/usr/bin",
        "/bin",
    ])
    existing = str(env.get("PATH") or "")
    path_parts: list[str] = []
    seen: set[str] = set()
    for part in [*prefixes, *existing.split(":")]:
        if part and part not in seen:
            seen.add(part)
            path_parts.append(part)
    env["PATH"] = ":".join(path_parts)
    return env


def _run_lean(path: Path, *, timeout_s: int) -> dict[str, Any]:
    cmd = ["lake", "env", "lean", str(path)]
    started = time.time()
    env = _lean_subprocess_env()
    project_root = _lean_project_root()
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=max(1, timeout_s), env=env, cwd=str(project_root))
        return {
            "cmd": ["lake", "env", "lean", str(path)],
            "cwd": str(project_root),
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-2000:],
            "stderr_tail": proc.stderr[-2000:],
            "timed_out": False,
            "wall_time_s": round(time.time() - started, 3),
        }
    except FileNotFoundError as exc:
        return {
            "cmd": ["lake", "env", "lean", str(path)],
            "cwd": str(project_root),
            "returncode": 127,
            "stdout_tail": "",
            "stderr_tail": f"missing executable: {exc.filename}; PATH={env.get('PATH', '')}"[-2000:],
            "timed_out": False,
            "wall_time_s": round(time.time() - started, 3),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": ["lake", "env", "lean", str(path)],
            "cwd": str(project_root),
            "returncode": 124,
            "stdout_tail": str(exc.stdout or "")[-2000:],
            "stderr_tail": (str(exc.stderr or "") + f"\nTimed out after {timeout_s}s")[-2000:],
            "timed_out": True,
            "wall_time_s": round(time.time() - started, 3),
        }


def _load_completed(path: str | Path, *, run_id: str, allow_mixed_run_id_checkpoint: bool = False) -> set[tuple[str, str]]:
    p = Path(path)
    if not p.exists():
        return set()
    completed: set[tuple[str, str]] = set()
    foreign_run_ids: set[str] = set()
    for line in p.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        rec_run_id = str(rec.get("run_id") or "")
        if rec_run_id and run_id and rec_run_id != run_id:
            foreign_run_ids.add(rec_run_id)
            continue
        row_id = str(rec.get("row_id") or "")
        arm = str(rec.get("arm") or "")
        if row_id and arm:
            completed.add((row_id, arm))
    if foreign_run_ids and not allow_mixed_run_id_checkpoint:
        raise SystemExit("evaluation harness checkpoint run_id mismatch: " + json.dumps({
            "checkpoint": str(path),
            "requested_run_id": run_id,
            "foreign_run_ids": sorted(foreign_run_ids),
        }, sort_keys=True))
    return completed


def _append_jsonl(path: str | Path, rec: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()


def _route_candidates(arm: dict[str, Any], *, max_calls: int) -> list[dict[str, Any]]:
    out = []
    for item in arm.get("route") or []:
        if not isinstance(item, dict):
            continue
        tactic = str(item.get("tactic") or "")
        if tactic:
            out.append({
                "candidate_kind": "tool_tactic",
                "candidate_id": str(item.get("tool_id") or tactic),
                "body": tactic,
                "timeout_s": int(item.get("default_timeout_s") or 20),
            })
        if len(out) >= max_calls:
            break
    return out


def _family_template_row_ids(specs: list[dict[str, Any]]) -> set[str]:
    out: set[str] = set()
    for spec in specs:
        for template in spec.get("templates") or []:
            if isinstance(template, dict) and str(template.get("test_kind") or "") == "positive":
                row_id = str(template.get("row_id") or "")
                if row_id:
                    out.add(row_id)
    return out


def _usable_specs_with_target_context(
    specs: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    target_names_by_row = _target_names_by_row_from_rows(rows)
    usable = family_specs.usable_specs(specs, target_names_by_row=target_names_by_row)
    target_reference_quarantines = [
        failure for failure in family_specs.validate_specs(specs, target_names_by_row=target_names_by_row)
        if str(failure.get("failure") or "") in TARGET_REFERENCE_TEMPLATE_FAILURES
    ]
    return usable, {
        "target_context_row_count": len(target_names_by_row),
        "usable_family_template_row_count": len(_family_template_row_ids(usable)),
        "target_reference_quarantine_count": len(target_reference_quarantines),
        "target_reference_quarantine_examples": target_reference_quarantines[:12],
        "rationale": "runner loads repair-family templates with selected-row target-name quarantine before residual-memory preflight or candidate generation",
    }


def _template_body_for_direct_lean(template: dict[str, Any]) -> str:
    lines: list[str] = []
    for line in family_specs._template_body(template):
        text = str(line)
        prefix, sep, rest = text.partition("::")
        if sep and prefix and "\n" not in prefix and len(prefix) <= 160:
            text = rest
        lines.append(text)
    return "\n".join(lines)


def _family_candidates(row_id: str, specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for spec in specs:
        family = str(spec.get("family") or "")
        templates = [t for t in (spec.get("templates") or []) if isinstance(t, dict) and str(t.get("row_id") or "") == row_id]
        negatives = [t for t in templates if str(t.get("test_kind") or "") == "negative_control"]
        for template in templates:
            if str(template.get("test_kind") or "") != "positive":
                continue
            body = _template_body_for_direct_lean(template)
            candidates.append({
                "candidate_kind": "repair_family_template",
                "candidate_id": str(template.get("id") or "positive_template"),
                "family": family,
                "body": body,
                "timeout_s": int(template.get("timeout") or 120),
                "negative_controls": [
                    {
                        "candidate_id": str(neg.get("id") or "negative_control"),
                        "body": _template_body_for_direct_lean(neg),
                        "timeout_s": int(neg.get("timeout") or 80),
                    }
                    for neg in negatives
                ],
            })
    return candidates


def _arm_candidates(
    arm: dict[str, Any],
    row_id: str,
    specs: list[dict[str, Any]],
    *,
    max_calls: int,
    fallback_family_call_budget: int = 3,
    residual_candidate_order: str = "family_first",
) -> list[dict[str, Any]]:
    route = _route_candidates(arm, max_calls=max_calls)
    if not bool(arm.get("uses_residual_memory")):
        return route
    family = _family_candidates(row_id, specs)
    if not family:
        return route
    family_budget = min(len(family), max(0, int(fallback_family_call_budget)), max_calls)
    if family_budget <= 0:
        return route
    tool_budget = max(0, max_calls - family_budget)
    order = str(arm.get("candidate_order") or residual_candidate_order or "family_first").strip()
    if order == "tool_first":
        return (route[:tool_budget] + family[:family_budget])[:max_calls]
    if order == "interleave":
        merged: list[dict[str, Any]] = []
        family_slice = family[:family_budget]
        route_slice = route[:tool_budget]
        for idx in range(max(len(family_slice), len(route_slice))):
            if idx < len(family_slice):
                merged.append(family_slice[idx])
            if idx < len(route_slice):
                merged.append(route_slice[idx])
        return merged[:max_calls]
    return (family[:family_budget] + route[:tool_budget])[:max_calls]


def _preflight_target_resolution(rows: list[dict[str, Any]]) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    checked = 0
    for row in rows:
        row_id = str(row.get("row_id") or "")
        source_file = Path(str(row.get("source_file") or ""))
        if not row_id:
            continue
        if not source_file.exists():
            failures.append({"row_id": row_id, "reason": "missing_source_file", "source_file": str(source_file)})
            continue
        text = source_file.read_text(errors="ignore")
        target_line = _target_line(row)
        checked += 1
        attempts: list[dict[str, Any]] = []
        resolved = ""
        for candidate_name in _row_theorem_name_candidates(row):
            attempt = _resolve_theorem_name(text, candidate_name, target_line)
            attempts.append(attempt)
            resolved = str(attempt.get("theorem_name") or "")
            if resolved:
                break
        if not resolved:
            failures.append({
                "row_id": row_id,
                "reason": "target_theorem_not_resolved",
                "source_file": str(source_file),
                "resolution_attempts": attempts[-3:],
            })
    return {
        "status": "pass" if not failures else "fail",
        "checked_row_count": checked,
        "failure_count": len(failures),
        "failures": failures[:20],
    }


def _preflight_residual_memory_coverage(
    *,
    rows: list[dict[str, Any]],
    arms: list[dict[str, Any]],
    specs: list[dict[str, Any]],
    min_family_template_rows: int,
) -> dict[str, Any]:
    uses_residual_memory = any(bool(arm.get("uses_residual_memory")) for arm in arms)
    selected_row_ids = [str(row.get("row_id") or "") for row in rows if str(row.get("row_id") or "")]
    template_row_ids = _family_template_row_ids(specs)
    overlap = [row_id for row_id in selected_row_ids if row_id in template_row_ids]
    return {
        "uses_residual_memory": uses_residual_memory,
        "selected_row_count": len(selected_row_ids),
        "family_template_selected_count": len(overlap),
        "min_family_template_rows": int(min_family_template_rows),
        "selected_template_rows": overlap,
        "status": (
            "pass"
            if (not uses_residual_memory or len(overlap) >= int(min_family_template_rows))
            else "fail"
        ),
    }


def _learning_exit(*, arm: dict[str, Any], positive_ok: bool, negative_results: list[dict[str, Any]], candidate_kind: str) -> str:
    if not positive_ok:
        return "tested_no_positive_signal"
    if not bool(arm.get("uses_governance_gate")):
        return "raw_closure_candidate"
    if candidate_kind != "repair_family_template":
        return "governed_tool_tactic_closure_candidate"
    if not negative_results:
        return "governance_rejected_missing_negative_control"
    if any(item.get("positive_unexpectedly_passed") for item in negative_results):
        return "failed_negative_control"
    return "ratified_closure"


def _run_row_arm(
    args: argparse.Namespace,
    *,
    row: dict[str, Any],
    arm: dict[str, Any],
    specs: list[dict[str, Any]],
    max_calls: int,
    run_root: Path,
    wall_timeout_s: int,
) -> dict[str, Any]:
    row_id = str(row.get("row_id") or "")
    arm_id = str(arm.get("arm") or "")
    target_kind = str(row.get("target_kind") or "")  # pre-reg hard failure #2 audit field
    uses_residual_memory = bool(arm.get("uses_residual_memory"))
    family_candidate_count = len(_family_candidates(row_id, specs)) if uses_residual_memory else 0
    candidates = _arm_candidates(
        arm,
        row_id,
        specs,
        max_calls=max_calls,
        fallback_family_call_budget=int(args.residual_fallback_family_call_budget),
        residual_candidate_order=str(getattr(args, "residual_candidate_order", "family_first") or "family_first"),
    )
    attempts: list[dict[str, Any]] = []
    row_started = time.monotonic()
    wall_timeout_hit = False
    for index, candidate in enumerate(candidates):
        # Pre-reg hard failure #5: enforce wall_timeout_s_per_row across the
        # whole row, not just per candidate. If the row has already burned its
        # budget, stop attempting and report wall_timeout_hit.
        elapsed = time.monotonic() - row_started
        if wall_timeout_s and elapsed >= wall_timeout_s:
            wall_timeout_hit = True
            break
        candidate_path = run_root / _slug(arm_id) / _slug(row_id) / f"candidate_{index}_{_slug(candidate['candidate_id'])}.lean"
        build = _build_candidate_file(row, str(candidate["body"]), candidate_path)
        if build.get("status") != "pass":
            attempts.append({
                "candidate_kind": candidate.get("candidate_kind"),
                "candidate_id": candidate.get("candidate_id"),
                "family": candidate.get("family"),
                "build": build,
            })
            continue
        # Cap per-candidate timeout by remaining wall budget so a single slow
        # candidate cannot blow past the row budget.
        remaining = max(1, int(wall_timeout_s - elapsed)) if wall_timeout_s else int(args.per_candidate_timeout_s)
        timeout_s = min(int(args.per_candidate_timeout_s), int(candidate.get("timeout_s") or args.per_candidate_timeout_s), remaining)
        result = _run_lean(candidate_path, timeout_s=timeout_s)
        positive_ok = result["returncode"] == 0
        negative_results: list[dict[str, Any]] = []
        if positive_ok and candidate.get("candidate_kind") == "repair_family_template":
            for neg_index, neg in enumerate(candidate.get("negative_controls") or []):
                # Honour the row-level wall budget for negative controls too.
                elapsed_neg = time.monotonic() - row_started
                if wall_timeout_s and elapsed_neg >= wall_timeout_s:
                    wall_timeout_hit = True
                    break
                neg_path = run_root / _slug(arm_id) / _slug(row_id) / f"negative_{index}_{neg_index}_{_slug(neg['candidate_id'])}.lean"
                neg_build = _build_candidate_file(row, str(neg["body"]), neg_path)
                if neg_build.get("status") != "pass":
                    negative_results.append({"candidate_id": neg["candidate_id"], "build": neg_build, "positive_unexpectedly_passed": False})
                    continue
                neg_remaining = max(1, int(wall_timeout_s - elapsed_neg)) if wall_timeout_s else int(args.per_candidate_timeout_s)
                neg_timeout = min(int(args.per_candidate_timeout_s), int(neg.get("timeout_s") or args.per_candidate_timeout_s), neg_remaining)
                neg_result = _run_lean(neg_path, timeout_s=neg_timeout)
                negative_results.append({
                    "candidate_id": neg["candidate_id"],
                    "returncode": neg_result["returncode"],
                    "timed_out": neg_result["timed_out"],
                    "positive_unexpectedly_passed": neg_result["returncode"] == 0,
                    "artifact": str(neg_path),
                })
        exit_kind = _learning_exit(
            arm=arm,
            positive_ok=positive_ok,
            negative_results=negative_results,
            candidate_kind=str(candidate.get("candidate_kind") or ""),
        )
        current_is_family_template = str(candidate.get("candidate_kind") or "") == "repair_family_template"
        family_reached = current_is_family_template or any(str(attempt.get("candidate_kind") or "") == "repair_family_template" for attempt in attempts)
        family_not_reached_reason = None
        if uses_residual_memory and family_candidate_count and not family_reached and exit_kind in {
            "raw_closure_candidate",
            "governed_tool_tactic_closure_candidate",
            "ratified_closure",
        }:
            family_not_reached_reason = "tool_positive_before_family"
        # Pre-reg hard failure #2 audit: if the row declares a target_kind,
        # check that the closure-shaped verdict is consistent with it.
        target_kind_audit: str | None = None
        if target_kind and exit_kind in {"ratified_closure", "governed_tool_tactic_closure_candidate", "raw_closure_candidate"}:
            if target_kind not in {"closure", "repair_canary"}:
                target_kind_audit = f"wrong_target_kind_credit:closure_on_{target_kind}"
                exit_kind = "target_kind_audit_failure"
        attempts.append({
            "candidate_kind": candidate.get("candidate_kind"),
            "candidate_id": candidate.get("candidate_id"),
            "family": candidate.get("family"),
            "artifact": str(candidate_path),
            "returncode": result["returncode"],
            "timed_out": result["timed_out"],
            "wall_time_s": result["wall_time_s"],
            "stderr_tail": result["stderr_tail"][-800:],
            "negative_results": negative_results,
            "learning_exit": exit_kind,
            "target_kind_audit": target_kind_audit,
        })
        if exit_kind in {"raw_closure_candidate", "ratified_closure", "failed_negative_control", "governed_tool_tactic_closure_candidate", "target_kind_audit_failure"}:
            return {
                "row_id": row_id,
                "tier": row.get("tier"),
                "target_kind": target_kind or "unknown",
                "arm": arm_id,
                "status": "done",
                "learning_exit": exit_kind,
                "closed": exit_kind in {"raw_closure_candidate", "ratified_closure", "governed_tool_tactic_closure_candidate"} and not target_kind_audit,
                "attempt_count": len(attempts),
                "candidate_count": len(candidates),
                "family_candidate_count": family_candidate_count,
                "family_reached": family_reached,
                "family_not_reached_reason": family_not_reached_reason,
                "residual_candidate_order": (
                    str(arm.get("candidate_order") or getattr(args, "residual_candidate_order", "family_first") or "family_first")
                    if uses_residual_memory else None
                ),
                "wall_time_used_s": round(time.monotonic() - row_started, 3),
                "wall_timeout_s": int(wall_timeout_s) if wall_timeout_s else None,
                "wall_timeout_hit": wall_timeout_hit,
                "target_kind_audit": target_kind_audit,
                "attempts": attempts,
            }
    build_failure_attempts = [
        attempt for attempt in attempts
        if isinstance(attempt.get("build"), dict) and attempt["build"].get("status") != "pass"
    ]
    lean_attempt_count = sum(1 for attempt in attempts if "returncode" in attempt)
    if wall_timeout_hit:
        exit_kind_final = "wall_timeout_hit"
    elif candidates and attempts and build_failure_attempts and lean_attempt_count == 0:
        exit_kind_final = "harness_candidate_build_failure"
    elif not candidates:
        exit_kind_final = "harness_no_candidates"
    else:
        exit_kind_final = "tested_no_positive_signal"
    family_reached = any(str(attempt.get("candidate_kind") or "") == "repair_family_template" for attempt in attempts)
    family_not_reached_reason = None
    if uses_residual_memory and family_candidate_count and not family_reached:
        if wall_timeout_hit:
            family_not_reached_reason = "wall_timeout_before_family"
        elif len(candidates) >= max_calls:
            family_not_reached_reason = "candidate_budget_excluded_family"
        else:
            family_not_reached_reason = "family_unreached_unknown"
    return {
        "row_id": row_id,
        "tier": row.get("tier"),
        "target_kind": target_kind or "unknown",
        "arm": arm_id,
        "status": "done",
        "learning_exit": exit_kind_final,
        "closed": False,
        "attempt_count": len(attempts),
        "candidate_count": len(candidates),
        "family_candidate_count": family_candidate_count,
        "family_reached": family_reached,
        "family_not_reached_reason": family_not_reached_reason,
        "residual_candidate_order": (
            str(arm.get("candidate_order") or getattr(args, "residual_candidate_order", "family_first") or "family_first")
            if uses_residual_memory else None
        ),
        "build_failure_count": len(build_failure_attempts),
        "lean_attempt_count": lean_attempt_count,
        "wall_time_used_s": round(time.monotonic() - row_started, 3),
        "wall_timeout_s": int(wall_timeout_s) if wall_timeout_s else None,
        "wall_timeout_hit": wall_timeout_hit,
        "attempts": attempts,
    }


def _positive_signal_count(records: list[dict[str, Any]]) -> int:
    return sum(1 for rec in records if str(rec.get("learning_exit") or "") in POSITIVE_SIGNAL_EXITS)


def _fully_completed_row_count(records: list[dict[str, Any]], arms: list[dict[str, Any]]) -> int:
    arm_ids = {str(arm.get("arm") or "") for arm in arms if str(arm.get("arm") or "")}
    if not arm_ids:
        return 0
    by_row: dict[str, set[str]] = defaultdict(set)
    for rec in records:
        row_id = str(rec.get("row_id") or "")
        arm_id = str(rec.get("arm") or "")
        if row_id and arm_id:
            by_row[row_id].add(arm_id)
    return sum(1 for seen in by_row.values() if arm_ids.issubset(seen))


def _load_run_records(path: str | Path, *, run_id: str) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in p.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
                continue
        if isinstance(obj, dict) and str(obj.get("run_id") or "") == run_id:
            out.append(obj)
    return out


def _residual_memory_observability(records: list[dict[str, Any]]) -> dict[str, Any]:
    residual_records = [
        rec for rec in records
        if int(rec.get("family_candidate_count") or 0) > 0
    ]
    masked = [
        rec for rec in residual_records
        if not bool(rec.get("family_reached"))
    ]
    reason_counts = Counter(str(rec.get("family_not_reached_reason") or "unknown") for rec in masked)
    family_reached = [rec for rec in residual_records if bool(rec.get("family_reached"))]
    tool_positive_before_family = [
        rec for rec in masked
        if str(rec.get("family_not_reached_reason") or "") == "tool_positive_before_family"
    ]
    if not residual_records:
        status = "not_applicable"
    elif masked:
        status = "fail"
    else:
        status = "pass"
    return {
        "schema": "leanmill-residual-memory-observability-v1",
        "status": status,
        "family_candidate_record_count": len(residual_records),
        "family_reached_record_count": len(family_reached),
        "masked_family_candidate_record_count": len(masked),
        "mask_reason_counts": dict(sorted(reason_counts.items())),
        "tool_positive_before_family_count": len(tool_positive_before_family),
        "sample_masked_records": [
            {
                "row_id": rec.get("row_id"),
                "arm": rec.get("arm"),
                "tier": rec.get("tier"),
                "learning_exit": rec.get("learning_exit"),
                "family_not_reached_reason": rec.get("family_not_reached_reason"),
                "residual_candidate_order": rec.get("residual_candidate_order"),
            }
            for rec in masked[:12]
        ],
    }


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _arm_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        by_arm[str(rec.get("arm") or "")].append(rec)
    out: dict[str, Any] = {}
    for arm, vals in sorted(by_arm.items()):
        row_count = len(vals)
        closed_count = sum(1 for rec in vals if bool(rec.get("closed")))
        ratified_count = sum(1 for rec in vals if str(rec.get("learning_exit") or "") == "ratified_closure")
        governed_tool_count = sum(1 for rec in vals if str(rec.get("learning_exit") or "") == "governed_tool_tactic_closure_candidate")
        raw_count = sum(1 for rec in vals if str(rec.get("learning_exit") or "") == "raw_closure_candidate")
        no_signal_count = sum(1 for rec in vals if str(rec.get("learning_exit") or "") == "tested_no_positive_signal")
        attempt_counts = [float(rec.get("attempt_count") or 0) for rec in vals]
        wall_times = [float(rec.get("wall_time_used_s") or 0.0) for rec in vals]
        family_records = [rec for rec in vals if int(rec.get("family_candidate_count") or 0) > 0]
        out[arm] = {
            "record_count": row_count,
            "closed_count": closed_count,
            "closure_rate": round(closed_count / row_count, 4) if row_count else 0.0,
            "ratified_closure_count": ratified_count,
            "ratified_closure_rate": round(ratified_count / row_count, 4) if row_count else 0.0,
            "governed_tool_tactic_closure_candidate_count": governed_tool_count,
            "raw_closure_candidate_count": raw_count,
            "tested_no_positive_signal_count": no_signal_count,
            "mean_attempt_count": _mean(attempt_counts),
            "mean_wall_time_s": _mean(wall_times),
            "family_candidate_record_count": len(family_records),
            "family_reached_record_count": sum(1 for rec in family_records if bool(rec.get("family_reached"))),
            "masked_family_candidate_record_count": sum(1 for rec in family_records if not bool(rec.get("family_reached"))),
        }
    baseline = out.get("governed_public_tool_static") or {}
    residual = out.get("governed_adaptive_residual_curriculum") or {}
    if baseline and residual:
        baseline_closure = float(baseline.get("closure_rate") or 0.0)
        residual_closure = float(residual.get("closure_rate") or 0.0)
        baseline_attempt = float(baseline.get("mean_attempt_count") or 0.0)
        residual_attempt = float(residual.get("mean_attempt_count") or 0.0)
        comparison = {
            "baseline_arm": "governed_public_tool_static",
            "residual_arm": "governed_adaptive_residual_curriculum",
            "closure_rate_delta": round(residual_closure - baseline_closure, 4),
            "attempt_efficiency_ratio_baseline_over_residual": round(baseline_attempt / residual_attempt, 4) if residual_attempt > 0 else None,
            "meets_20pp_closure_lift": (residual_closure - baseline_closure) >= 0.20,
            "meets_2x_attempt_efficiency_lift": (baseline_attempt / residual_attempt) >= 2.0 if residual_attempt > 0 else False,
            "interpretation": "efficiency ratio >1 means residual arm used fewer attempts on average than governed public static baseline",
        }
    else:
        comparison = {}
    return {
        "schema": "leanmill-evaluation-arm-metrics-v1",
        "arms": out,
        "benchmark_lift_comparison": comparison,
        "credit_boundary": "public/static closure is baseline evidence, not LeanMill proof credit; ratified_closure is the governed repair-template credit surface",
    }


def _benchmark_claim_class(
    *,
    completed_row_count: int,
    positive_signal_count: int,
    arm_metrics: dict[str, Any],
    contract_sha_check: dict[str, Any] | None,
    tool_universe_check: dict[str, Any] | None,
    snapshot_receipt: dict[str, Any] | None,
    target_resolution_check: dict[str, Any] | None,
    policy: dict[str, Any],
) -> dict[str, Any]:
    policy = policy if isinstance(policy, dict) else {}
    smoke_max = int(policy.get("smoke_completed_row_max") or 2)
    internal_min = int(policy.get("internal_benchmark_min_completed_rows") or 5)
    publishable_min = int(policy.get("publishable_benchmark_min_completed_rows") or 20)
    comparison = (arm_metrics.get("benchmark_lift_comparison") or {}) if isinstance(arm_metrics, dict) else {}
    prereq_checks = {
        "contract_sha256_verified": bool(contract_sha_check and contract_sha_check.get("status") == "pass"),
        "tool_universe_validated": bool(tool_universe_check and tool_universe_check.get("status") == "pass"),
        "repair_families_air_gapped": bool(snapshot_receipt and snapshot_receipt.get("status") == "ok"),
        "target_resolution_preflight_passed": bool(target_resolution_check and target_resolution_check.get("status") == "pass"),
    }
    prereqs_ok = all(prereq_checks.values())
    lift_gate = bool(comparison.get("meets_20pp_closure_lift") or comparison.get("meets_2x_attempt_efficiency_lift"))
    if completed_row_count <= smoke_max:
        claim_class = "integration_smoke_only"
        allowed_claim = "wiring_health_only"
    elif completed_row_count < publishable_min or not prereqs_ok or not lift_gate:
        claim_class = "internal_benchmark_slice"
        allowed_claim = "internal_measurement_only"
    else:
        claim_class = "publishable_benchmark_lift_candidate"
        allowed_claim = "candidate_lift_claim_pending_human_review"
    disqualifiers: list[str] = []
    if completed_row_count <= smoke_max:
        disqualifiers.append("completed_rows_at_or_below_smoke_threshold")
    if completed_row_count < internal_min:
        disqualifiers.append("below_internal_benchmark_min_completed_rows")
    if completed_row_count < publishable_min:
        disqualifiers.append("below_publishable_benchmark_min_completed_rows")
    for key, ok in prereq_checks.items():
        if not ok:
            disqualifiers.append(key + "_missing")
    if not lift_gate:
        disqualifiers.append("lift_gate_not_met_or_not_applicable")
    return {
        "schema": "leanmill-evaluation-harness-claim-class-v1",
        "claim_class": claim_class,
        "allowed_claim": allowed_claim,
        "completed_row_count": completed_row_count,
        "positive_signal_count": positive_signal_count,
        "policy": {
            "smoke_completed_row_max": smoke_max,
            "internal_benchmark_min_completed_rows": internal_min,
            "publishable_benchmark_min_completed_rows": publishable_min,
        },
        "prereq_checks": prereq_checks,
        "lift_gate": lift_gate,
        "disqualifiers": disqualifiers,
        "credit_boundary": str(policy.get("credit_boundary") or "Small runs are integration evidence only; benchmark lift requires policy gates."),
        "rationale": str(policy.get("rationale") or ""),
    }


def _summarize(records: list[dict[str, Any]], *, args: argparse.Namespace, prep: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    by_arm: dict[str, Counter[str]] = defaultdict(Counter)
    by_arm_tier: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    for rec in records:
        arm = str(rec.get("arm") or "")
        tier = str(rec.get("tier") or "")
        exit_kind = str(rec.get("learning_exit") or "")
        by_arm[arm][exit_kind] += 1
        by_arm_tier[arm][tier][exit_kind] += 1
    # Surface the pre-flight verifications that ran at the start of `run()`,
    # if available (they live on args after run() runs).
    contract_sha_check = getattr(args, "_contract_sha256_check", None)
    tool_universe_check = getattr(args, "_tool_universe_check", None)
    snapshot_receipt = getattr(args, "_snapshot_receipt", None)
    toolchain_versions = getattr(args, "_toolchain_versions", None)
    target_resolution_check = getattr(args, "_target_resolution_check", None)
    wall_timeout_s = getattr(args, "_wall_timeout_s", None)
    spec_dir_in_use = getattr(args, "_spec_dir_in_use", args.spec_dir)
    selected_rows = _selected_rows(
        prep,
        _read_json(prep.get("row_context") or "") or {},
        limit=args.limit,
    )
    summary_specs, summary_target_filter = _usable_specs_with_target_context(
        family_specs.load_specs(spec_dir_in_use),
        selected_rows,
    )
    selected_row_count = len({str(r.get("row_id") or "") for r in selected_rows if str(r.get("row_id") or "")})
    completed_row_count = len({str(r.get("row_id") or "") for r in records if str(r.get("row_id") or "")})
    preflight_only = bool(getattr(args, "preflight_only", False))
    residual_candidate_order = str(getattr(args, "residual_candidate_order", "family_first") or "family_first")
    residual_observability = _residual_memory_observability(records)
    arm_metrics = _arm_metrics(records)
    claim_class = _benchmark_claim_class(
        completed_row_count=completed_row_count,
        positive_signal_count=_positive_signal_count(records),
        arm_metrics=arm_metrics,
        contract_sha_check=contract_sha_check,
        tool_universe_check=tool_universe_check,
        snapshot_receipt=snapshot_receipt,
        target_resolution_check=target_resolution_check,
        policy=_policy_dict("evaluation_harness_claim_class_policy", path=getattr(args, "factory_policy", FACTORY_POLICY)),
    )
    return {
        "schema": "leanmill-evaluation-harness-run-v1",
        "generated_at_epoch": int(time.time()),
        "prep": args.prep,
        "contract": args.contract,
        "checkpoint": args.checkpoint,
        "row_limit": args.limit,
        "row_count": selected_row_count if preflight_only else completed_row_count,
        "selected_row_count": selected_row_count,
        "completed_row_count": completed_row_count,
        "record_count": len(records),
        "contract_hash": prep.get("contract_hash") or contract.get("contract_hash"),
        "contract_sha256_check": contract_sha_check,
        "tool_universe_check": tool_universe_check,
        "repair_families_snapshot": snapshot_receipt,
        "toolchain_versions": toolchain_versions,
        "target_resolution_check": target_resolution_check,
        "wall_timeout_s_per_row": wall_timeout_s,
        "spec_dir_in_use": spec_dir_in_use,
        "target_aware_family_template_filter": getattr(args, "_target_aware_family_template_filter", summary_target_filter),
        "residual_fallback_family_call_budget": int(getattr(args, "residual_fallback_family_call_budget", 0) or 0),
        "residual_candidate_order": residual_candidate_order,
        "benchmark_readiness": contract.get("benchmark_readiness"),
        "same_tool_universe": bool(contract.get("same_tool_universe")),
        "same_governance_gate": bool(contract.get("same_governance_gate")),
        "same_budget": bool(contract.get("same_budget")),
        "residual_memory_preflight": _preflight_residual_memory_coverage(
            rows=selected_rows,
            arms=[arm for arm in (contract.get("arms") or []) if isinstance(arm, dict)],
            specs=summary_specs,
            min_family_template_rows=int(args.min_family_template_rows),
        ),
        "residual_memory_observability": residual_observability,
        "arm_metrics": arm_metrics,
        "benchmark_claim_class": claim_class,
        "by_arm": {arm: dict(counter) for arm, counter in sorted(by_arm.items())},
        "by_arm_tier": {
            arm: {tier: dict(counter) for tier, counter in sorted(tiers.items())}
            for arm, tiers in sorted(by_arm_tier.items())
        },
        "positive_signal_count": _positive_signal_count(records),
        "fully_completed_row_count": _fully_completed_row_count(
            records,
            [arm for arm in (contract.get("arms") or []) if isinstance(arm, dict)],
        ),
        "early_stop": getattr(args, "_early_stop", None),
        "harness_infra": {
            "candidate_build_failure_record_count": sum(1 for rec in records if rec.get("learning_exit") == "harness_candidate_build_failure"),
            "no_candidates_record_count": sum(1 for rec in records if rec.get("learning_exit") == "harness_no_candidates"),
            "candidate_build_failure_attempt_count": sum(
                1
                for rec in records
                for attempt in rec.get("attempts", [])
                if isinstance(attempt.get("build"), dict) and attempt["build"].get("status") != "pass"
            ),
        },
        "no_laundering": {
            "public_tool_static_has_no_leanmill_credit": True,
            "governed_credit_requires_compile_and_negative_controls_for_repair_templates": True,
            "runner_does_not_update_registry": True,
            "candidate_build_failures_not_counted_as_no_signal": True,
            "contract_sha256_verified": bool(contract_sha_check and contract_sha_check.get("status") == "pass"),
            "tool_universe_validated": bool(tool_universe_check and tool_universe_check.get("status") == "pass"),
            "target_resolution_preflight_passed": bool(target_resolution_check and target_resolution_check.get("status") == "pass"),
            "target_aware_family_template_filter_active": bool(
                getattr(args, "_target_aware_family_template_filter", summary_target_filter)
            ),
            "benchmark_lift_claim_blocked_unless_claim_class_allows": claim_class.get("claim_class") != "publishable_benchmark_lift_candidate",
            "repair_families_air_gapped": bool(snapshot_receipt and snapshot_receipt.get("status") == "ok"),
            "residual_memory_family_candidates_observed_before_tool_credit": (
                residual_observability.get("status") in {"pass", "not_applicable"}
            ),
        },
    }


def _write_markdown(path: str | Path, summary: dict[str, Any]) -> None:
    lines = [
        "# LeanMill Evaluation Harness Run",
        "",
        f"- generated_at_epoch: `{summary['generated_at_epoch']}`",
        f"- row_count: `{summary['row_count']}`",
        f"- selected_row_count: `{summary.get('selected_row_count')}`",
        f"- completed_row_count: `{summary.get('completed_row_count')}`",
        f"- record_count: `{summary['record_count']}`",
        f"- positive_signal_count: `{summary.get('positive_signal_count')}`",
        f"- fully_completed_row_count: `{summary.get('fully_completed_row_count')}`",
        f"- early_stop: `{summary.get('early_stop')}`",
        f"- checkpoint: `{summary['checkpoint']}`",
        f"- same_tool_universe: `{summary['same_tool_universe']}`",
        f"- same_governance_gate: `{summary['same_governance_gate']}`",
        f"- same_budget: `{summary['same_budget']}`",
        f"- residual_fallback_family_call_budget: `{summary.get('residual_fallback_family_call_budget')}`",
        f"- residual_candidate_order: `{summary.get('residual_candidate_order')}`",
        f"- residual_memory_observability: `{summary.get('residual_memory_observability', {}).get('status')}`",
        f"- masked_family_candidate_record_count: `{summary.get('residual_memory_observability', {}).get('masked_family_candidate_record_count')}`",
        f"- benchmark_lift_comparison: `{summary.get('arm_metrics', {}).get('benchmark_lift_comparison', {})}`",
        f"- benchmark_claim_class: `{summary.get('benchmark_claim_class', {}).get('claim_class')}`",
        f"- allowed_claim: `{summary.get('benchmark_claim_class', {}).get('allowed_claim')}`",
        "",
        "## By Arm",
        "",
    ]
    for arm, counts in summary["by_arm"].items():
        lines.append(f"- `{arm}`: `{counts}`")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    prep = _read_json(args.prep) or {}
    contract_path = args.contract or prep.get("contract") or DEFAULT_CONTRACT
    contract = _read_json(contract_path) or {}

    # Pre-reg hard failure #1: verify the contract on disk matches its pinned hash.
    # Skippable for debug/dry-runs via --skip-contract-sha-check; default is strict.
    contract_sha_check = _verify_contract_sha256(contract_path, contract)
    if contract_sha_check["status"] == "fail" and not args.skip_contract_sha_check:
        raise SystemExit("evaluation harness contract SHA256 mismatch: " + json.dumps({
            **contract_sha_check,
            "contract_path": str(contract_path),
            "hint": "the file was edited after pinning; re-pin contract_sha256 inside the file, or pass --skip-contract-sha-check for a non-credited dry-run",
        }, sort_keys=True))

    # Pre-reg hard failure #4: tool-universe validation per arm.
    tool_universe_check = _verify_tool_universe(contract)
    if tool_universe_check["status"] == "fail" and not args.skip_tool_universe_check:
        raise SystemExit("evaluation harness tool-universe violation: " + json.dumps({
            **tool_universe_check,
            "hint": "every arm's route tactic must be declared in contract.tool_universe; pass --skip-tool-universe-check for a non-credited dry-run",
        }, sort_keys=True))

    row_context = _read_json(prep.get("row_context") or "") or {}

    # Pre-reg hard failure #3: optional air-gap of repair_families against
    # mid-run edits by the live 24x7 mill. Off by default (no behavior change
    # for existing dry-runs); credited runs should pass --snapshot-repair-families-dir.
    spec_dir_in_use = args.spec_dir
    snapshot_receipt: dict[str, Any] | None = None
    effective_run_id_seed = args.run_id or str(int(time.time()))
    if args.snapshot_repair_families_dir:
        snapshot_receipt = _snapshot_repair_families(
            args.spec_dir, args.snapshot_repair_families_dir, effective_run_id_seed
        )
        if snapshot_receipt.get("status") == "ok":
            spec_dir_in_use = snapshot_receipt["snapshot_dir"]
        else:
            raise SystemExit("evaluation harness repair-families snapshot failed: " + json.dumps(
                snapshot_receipt, sort_keys=True
            ))

    arms = [arm for arm in (contract.get("arms") or []) if isinstance(arm, dict)]
    rows = _selected_rows(prep, row_context, limit=args.limit)
    specs, target_filter = _usable_specs_with_target_context(
        family_specs.load_specs(spec_dir_in_use),
        rows,
    )
    preflight = _preflight_residual_memory_coverage(
        rows=rows,
        arms=arms,
        specs=specs,
        min_family_template_rows=int(args.min_family_template_rows),
    )
    target_resolution_check = _preflight_target_resolution(rows)
    if target_resolution_check["status"] != "pass" and not args.skip_target_resolution_check:
        raise SystemExit("evaluation harness target-resolution preflight failed: " + json.dumps(target_resolution_check, sort_keys=True))
    max_calls = int((contract.get("budget") or {}).get("max_tool_calls_per_row") or args.max_tool_calls)
    # Pre-reg hard failure #5: wall_timeout_s_per_row from contract, with a
    # CLI override only for debug.
    wall_timeout_s = int(
        args.wall_timeout_s_per_row
        if args.wall_timeout_s_per_row > 0
        else (contract.get("budget") or {}).get("wall_timeout_s_per_row") or 180
    )
    toolchain_versions = _capture_toolchain_versions(spec_dir_in_use)
    run_root = Path(args.root) / str(args.run_id or int(time.time()))
    effective_run_id = str(args.run_id or run_root.name)
    bypass_allowed = bool(args.allow_no_family_template_rows) and int(args.min_family_template_rows) <= 0
    if preflight["status"] != "pass" and not bypass_allowed:
        raise SystemExit("evaluation harness preflight failed: " + json.dumps({
            **preflight,
            "bypass_rejected": bool(args.allow_no_family_template_rows),
            "bypass_rule": "debug bypass is accepted only when min_family_template_rows <= 0; prereg/residual-memory runs must use template-backed rows",
            "run_id": effective_run_id,
        }, sort_keys=True))
    # Expose the verified values via args so _summarize can read them without
    # re-computing.
    args._contract_sha256_check = contract_sha_check
    args._tool_universe_check = tool_universe_check
    args._snapshot_receipt = snapshot_receipt
    args._toolchain_versions = toolchain_versions
    args._target_resolution_check = target_resolution_check
    args._wall_timeout_s = wall_timeout_s
    args._spec_dir_in_use = spec_dir_in_use
    args._target_aware_family_template_filter = target_filter
    if args.preflight_only:
        summary = _summarize([], args=args, prep=prep, contract=contract)
        summary["preflight_only"] = True
        summary["run_id"] = effective_run_id
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _write_markdown(args.md, summary)
        return summary
    if args.summarize_only:
        summary_records = _load_run_records(args.checkpoint, run_id=effective_run_id)
        summary = _summarize(summary_records, args=args, prep=prep, contract=contract)
        summary["summarize_only"] = True
        summary["run_id"] = effective_run_id
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _write_markdown(args.md, summary)
        return summary
    completed = _load_completed(
        args.checkpoint,
        run_id=effective_run_id,
        allow_mixed_run_id_checkpoint=bool(args.allow_mixed_run_id_checkpoint),
    )
    Path(args.checkpoint).parent.mkdir(parents=True, exist_ok=True)
    lock_path = Path(args.lean_slot_lock)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    args._early_stop = None
    with lock_path.open("w") as lock_fh:
        if args.use_lean_slot_lock:
            fcntl.flock(lock_fh, fcntl.LOCK_EX)
        stop_run = False
        for row in rows:
            row_id = str(row.get("row_id") or "")
            if not row_id:
                continue
            for arm in arms:
                arm_id = str(arm.get("arm") or "")
                if not arm_id or (row_id, arm_id) in completed:
                    continue
                rec = _run_row_arm(
                    args,
                    row=row,
                    arm=arm,
                    specs=specs,
                    max_calls=max_calls,
                    run_root=run_root,
                    wall_timeout_s=wall_timeout_s,
                )
                rec["run_id"] = effective_run_id
                rec["contract"] = args.contract
                rec["created_at_epoch"] = int(time.time())
                _append_jsonl(args.checkpoint, rec)
                records.append(rec)
            all_run_records = _load_run_records(args.checkpoint, run_id=effective_run_id)
            completed_rows_now = _fully_completed_row_count(all_run_records, arms)
            positive_signals_now = _positive_signal_count(all_run_records)
            if (
                int(args.nonprobative_stop_completed_rows) > 0
                and completed_rows_now >= int(args.nonprobative_stop_completed_rows)
                and positive_signals_now < int(args.nonprobative_stop_min_positive_signals)
            ):
                args._early_stop = {
                    "class": "benchmark_slice_nonprobative_no_positive_support",
                    "completed_row_count": completed_rows_now,
                    "positive_signal_count": positive_signals_now,
                    "min_positive_signal_count": int(args.nonprobative_stop_min_positive_signals),
                    "stop_completed_rows": int(args.nonprobative_stop_completed_rows),
                }
                stop_run = True
                break
        if stop_run:
            pass
        if args.use_lean_slot_lock:
            fcntl.flock(lock_fh, fcntl.LOCK_UN)
    all_records: list[dict[str, Any]] = []
    p = Path(args.checkpoint)
    if p.exists():
        for line in p.read_text(errors="ignore").splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and str(obj.get("run_id") or "") == effective_run_id:
                all_records.append(obj)
    summary = _summarize(all_records, args=args, prep=prep, contract=contract)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(args.md, summary)
    return summary


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="leanmill_eval_harness_") as td:
        root = Path(td)
        source = root / "S.lean"
        source.write_text("theorem demo : True := by\n  trivial\n\ntheorem after : True := by\n  trivial\n")
        row = {"row_id": "r1", "goal": "theorem demo : True := by", "source_file": str(source)}
        out = root / "candidate.lean"
        receipt = _build_candidate_file(row, "trivial", out)
        assert receipt["status"] == "pass", receipt
        text = out.read_text()
        assert "theorem demo : True := by\n  trivial\n" in text
        assert "theorem after" not in text
        assert _template_body_for_direct_lean({"id": "demo_template", "body": "trivial"}) == "trivial"
        assert _template_body_for_direct_lean({"id": "demo_template", "body_lines": ["demo_template::trivial"]}) == "trivial"
        source2 = root / "S2.lean"
        source2.write_text("theorem long_name_suffix_extra : True := by\n  trivial\n")
        receipt2 = _build_candidate_file({"row_id": "MCB_001_long_name_suffix_", "source_file": str(source2)}, "trivial", root / "candidate2.lean")
        assert receipt2["status"] == "pass" and receipt2["theorem_name"] == "long_name_suffix_extra", receipt2
        source3 = root / "S3.lean"
        source3.write_text("theorem le_sum_schlomilch' : True := by\n  trivial\n")
        receipt3 = _build_candidate_file({"row_id": "MCB_001_le_sum_schlomilch_", "goal": "theorem le_sum_schlomilch' : True := by", "source_file": str(source3)}, "trivial", root / "candidate3.lean")
        assert receipt3["status"] == "pass" and receipt3["theorem_name"] == "le_sum_schlomilch'", receipt3
        source4 = root / "S4.lean"
        source4.write_text("noncomputable theorem Foo.bar₁' : True := by\n  trivial\n")
        receipt4 = _build_candidate_file({"row_id": "MCB_001_Foo.bar", "goal": "theorem Foo.bar₁' : True := by", "source_file": str(source4)}, "trivial", root / "candidate4.lean")
        assert receipt4["status"] == "pass" and receipt4["theorem_name"] == "Foo.bar₁'", receipt4
        source5 = root / "S5.lean"
        source5.write_text("theorem stem_alpha : True := by\n  trivial\n\ntheorem stem_beta : True := by\n  trivial\n")
        receipt5 = _build_candidate_file({"row_id": "MCB_001_stem_", "source": {"mathlib_name": "stem_beta"}, "source_file": str(source5)}, "trivial", root / "candidate5.lean")
        assert receipt5["status"] == "pass" and receipt5["theorem_name"] == "stem_beta", receipt5
        src6 = root / "ambiguous_line.lean"
        src6.write_text("theorem Foo.alpha : True := by\n  trivial\n\ntheorem Foo.beta : True := by\n  trivial\n")
        receipt6 = _build_candidate_file({"source_file": str(src6), "target_name": "Foo", "target_line": 4}, "trivial", root / "out6.lean")
        assert receipt6["status"] == "pass" and receipt6["theorem_name"] == "Foo.beta", receipt6
        assert receipt6["resolution"]["status"] == "target_line_nearest", receipt6
        arm = {"arm": "governed_adaptive_residual_curriculum", "uses_residual_memory": True, "route": [{"tool_id": "rfl", "tactic": "rfl"}]}
        candidates = _arm_candidates(arm, "r1", [], max_calls=1)
        assert candidates[0]["candidate_id"] == "rfl"
        spec = {"family": "fam", "templates": [{"id": "fam_pos", "row_id": "r1", "test_kind": "positive", "body_lines": ["trivial"]}]}
        fallback = _arm_candidates(arm, "r1", [spec], max_calls=3, fallback_family_call_budget=1)
        assert [c["candidate_kind"] for c in fallback] == ["repair_family_template", "tool_tactic"], fallback
        assert fallback[0]["candidate_id"] == "fam_pos", fallback
        leaky_spec = {
            "family": "leaky",
            "version": 1,
            "status": "seed_only",
            "credit": {"source_credit_eligible": False, "clean_solver_credit_eligible": False},
            "templates": [
                {"id": "leaky_pos", "row_id": "r1", "test_kind": "positive", "backend": "repl_file", "timeout": 10, "body": "exact demo"},
                {"id": "leaky_neg", "row_id": "r1", "test_kind": "negative_control", "backend": "repl_file", "timeout": 10, "body": "trivial"},
            ],
        }
        target_filtered_specs, target_filter = _usable_specs_with_target_context(
            [leaky_spec],
            [{"row_id": "r1", "target_theorem_name": "demo", "source_file": str(source)}],
        )
        assert target_filter["target_reference_quarantine_count"] == 1, target_filter
        assert _family_candidates("r1", target_filtered_specs) == [], target_filtered_specs
        tool_first = _arm_candidates(
            arm,
            "r1",
            [spec],
            max_calls=3,
            fallback_family_call_budget=1,
            residual_candidate_order="tool_first",
        )
        assert [c["candidate_kind"] for c in tool_first] == ["tool_tactic", "repair_family_template"], tool_first
        class Args:
            residual_fallback_family_call_budget = 0
            per_candidate_timeout_s = 10
            residual_candidate_order = "family_first"
        bad = _run_row_arm(
            Args(),
            row={"row_id": "bad", "source_file": str(root / "missing.lean")},
            arm={"arm": "public_tool_static", "route": [{"tool_id": "simp", "tactic": "simp"}]},
            specs=[],
            max_calls=1,
            run_root=root / "run",
            wall_timeout_s=10,
        )
        assert bad["learning_exit"] == "harness_candidate_build_failure", bad
        assert bad["build_failure_count"] == 1 and bad["lean_attempt_count"] == 0, bad
        preflight_resolution = _preflight_target_resolution([{"row_id": "MCB_001_stem_", "source_file": str(source5)}])
        assert preflight_resolution["status"] == "fail", preflight_resolution
        preflight_resolution_ok = _preflight_target_resolution([{"row_id": "MCB_001_stem_", "source": {"mathlib_name": "stem_beta"}, "source_file": str(source5)}])
        assert preflight_resolution_ok["status"] == "pass", preflight_resolution_ok
        wrong_kind = _run_row_arm(
            Args(),
            row={"row_id": "r1", "goal": "theorem demo : True := by", "source_file": str(source), "target_kind": "exact_gap"},
            arm={"arm": "public_tool_static", "route": [{"tool_id": "trivial", "tactic": "trivial"}]},
            specs=[],
            max_calls=1,
            run_root=root / "wrong_kind",
            wall_timeout_s=10,
        )
        assert wrong_kind["learning_exit"] == "target_kind_audit_failure" and wrong_kind["closed"] is False, wrong_kind
        class FamilyArgs:
            residual_fallback_family_call_budget = 1
            per_candidate_timeout_s = 10
            residual_candidate_order = "family_first"
        observed = _run_row_arm(
            FamilyArgs(),
            row=row,
            arm={"arm": "governed_adaptive_residual_curriculum", "uses_residual_memory": True, "route": [{"tool_id": "trivial", "tactic": "trivial"}]},
            specs=[spec],
            max_calls=2,
            run_root=root / "observed_family",
            wall_timeout_s=10,
        )
        assert observed["family_candidate_count"] == 1, observed
        assert observed["family_reached"] is True, observed
        assert observed["family_not_reached_reason"] is None, observed
        class ToolFirstArgs:
            residual_fallback_family_call_budget = 1
            per_candidate_timeout_s = 10
            residual_candidate_order = "tool_first"
        starved = _run_row_arm(
            ToolFirstArgs(),
            row=row,
            arm={"arm": "governed_adaptive_residual_curriculum", "uses_residual_memory": True, "route": [{"tool_id": "trivial", "tactic": "trivial"}]},
            specs=[spec],
            max_calls=2,
            run_root=root / "starved_family",
            wall_timeout_s=10,
        )
        assert starved["family_candidate_count"] == 1, starved
        assert starved["family_reached"] is False, starved
        assert starved["family_not_reached_reason"] == "tool_positive_before_family", starved
        assert _selected_rows({"selected_rows_order": ["r1", "r2"], "tiers": {"t": [{"row_id": "r1"}, {"row_id": "r2"}]}}, {}, limit=0)
        assert len(_selected_rows({"selected_rows_order": ["r1", "r2"], "tiers": {"t": [{"row_id": "r1"}, {"row_id": "r2"}]}}, {}, limit=0)) == 2
        obs = _residual_memory_observability([starved, observed])
        assert obs["status"] == "fail" and obs["masked_family_candidate_record_count"] == 1, obs
        metrics = _arm_metrics([starved, observed])
        assert metrics["arms"]["governed_adaptive_residual_curriculum"]["family_candidate_record_count"] == 2, metrics
        smoke_claim = _benchmark_claim_class(
            completed_row_count=1,
            positive_signal_count=4,
            arm_metrics=metrics,
            contract_sha_check={"status": "pass"},
            tool_universe_check={"status": "pass"},
            snapshot_receipt={"status": "ok"},
            target_resolution_check={"status": "pass"},
            policy={"smoke_completed_row_max": 2, "publishable_benchmark_min_completed_rows": 20},
        )
        assert smoke_claim["claim_class"] == "integration_smoke_only", smoke_claim
        assert "completed_rows_at_or_below_smoke_threshold" in smoke_claim["disqualifiers"], smoke_claim
    print("leanmill_evaluation_harness_runner self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prep", default=DEFAULT_PREP)
    ap.add_argument("--contract", default=DEFAULT_CONTRACT)
    ap.add_argument("--spec-dir", default=DEFAULT_SPEC_DIR)
    ap.add_argument("--min-family-template-rows", type=int, default=_policy_int("evaluation_harness_min_family_template_rows", 1))
    ap.add_argument("--allow-no-family-template-rows", action="store_true")
    ap.add_argument("--allow-mixed-run-id-checkpoint", action="store_true")
    ap.add_argument("--checkpoint", default=DEFAULT_CHECKPOINT)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--md", default=DEFAULT_MD)
    ap.add_argument("--factory-policy", default=FACTORY_POLICY)
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--run-id", default="")
    ap.add_argument("--limit", type=int, default=0, help="selected-row limit; 0 means all prepped selected rows")
    ap.add_argument("--max-tool-calls", type=int, default=4)
    ap.add_argument("--per-candidate-timeout-s", type=int, default=30)
    ap.add_argument(
        "--wall-timeout-s-per-row",
        type=int,
        default=0,
        help="row-level wall timeout in seconds (pre-reg hard failure #5); 0 = read from contract.budget.wall_timeout_s_per_row (default 180)",
    )
    ap.add_argument(
        "--skip-contract-sha-check",
        action="store_true",
        help="DEBUG ONLY. Skip pre-reg contract SHA256 verification. Credited runs must NOT pass this.",
    )
    ap.add_argument(
        "--skip-tool-universe-check",
        action="store_true",
        help="DEBUG ONLY. Skip pre-reg tool-universe validation. Credited runs must NOT pass this.",
    )
    ap.add_argument(
        "--skip-target-resolution-check",
        action="store_true",
        help="DEBUG ONLY. Skip selected-row target declaration resolution. Credited runs must NOT pass this.",
    )
    ap.add_argument(
        "--snapshot-repair-families-dir",
        default="",
        help="If set, copy --spec-dir into a content-addressed snapshot under this root and load specs from the snapshot, air-gapping the credited run against mid-run edits by the live 24x7 mill.",
    )
    ap.add_argument("--lean-slot-lock", default=DEFAULT_LOCK)
    ap.add_argument("--use-lean-slot-lock", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--residual-fallback-family-call-budget", type=int, default=_policy_int("evaluation_harness_residual_fallback_family_call_budget", 3))
    ap.add_argument(
        "--residual-candidate-order",
        choices=("family_first", "tool_first", "interleave"),
        default=_policy_str("evaluation_harness_residual_candidate_order", "family_first"),
        help="candidate ordering for residual-memory arms; credited runs default to family_first so repair-family lift is observable before generic tool credit",
    )
    ap.add_argument("--nonprobative-stop-completed-rows", type=int, default=_policy_int("evaluation_harness_nonprobative_stop_completed_rows", 20))
    ap.add_argument("--nonprobative-stop-min-positive-signals", type=int, default=_policy_int("evaluation_harness_nonprobative_stop_min_positive_signals", 1))
    ap.add_argument("--preflight-only", action="store_true")
    ap.add_argument("--summarize-only", action="store_true", help="Summarize an existing checkpoint for the selected run id without executing any row/arm work.")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    summary = run(args)
    print(json.dumps({
        "out": args.out,
        "md": args.md,
        "checkpoint": args.checkpoint,
        "row_count": summary["row_count"],
        "record_count": summary["record_count"],
        "preflight_only": bool(summary.get("preflight_only")),
        "by_arm": summary["by_arm"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
