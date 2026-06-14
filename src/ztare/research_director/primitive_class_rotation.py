"""Primitive-class rotation ledger shared by autoresearch and RD work.

The in-loop mutator uses this to avoid repeatedly refining one proposal class.
Out-of-loop RD tools use the same ledger to generate eigenquestions and inspect
which mechanism families have already been tried.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class PrimitiveClassRotationDeclaration:
    """One textual contract that means "record this as a class move"."""

    name: str
    pattern: re.Pattern[str]


@dataclass(frozen=True)
class PrimitiveClassTrackingResult:
    """Outcome of one primitive-class rotation tracking attempt."""

    enabled: bool
    should_track: bool
    tracked: bool
    class_name: Optional[str]
    reason: str


_PRIMITIVE_CLASS_ROTATION_DECLARATIONS: tuple[PrimitiveClassRotationDeclaration, ...] = (
    PrimitiveClassRotationDeclaration(
        "mechanism_field",
        re.compile(r"\bmechanism\s*=\s*propose_new_primitive_class\b", re.IGNORECASE),
    ),
    PrimitiveClassRotationDeclaration(
        "mechanism_literal",
        re.compile(r"\bpropose_new_primitive_class\b", re.IGNORECASE),
    ),
    PrimitiveClassRotationDeclaration(
        "structural_pivot_heading",
        re.compile(r"^\s*#{0,6}\s*structural\s+pivot\b", re.IGNORECASE | re.MULTILINE),
    ),
    PrimitiveClassRotationDeclaration(
        "structural_mutation_heading",
        re.compile(r"^\s*#{0,6}\s*structural\s+mutation\b", re.IGNORECASE | re.MULTILINE),
    ),
    PrimitiveClassRotationDeclaration(
        "category_switch_heading",
        re.compile(r"^\s*#{0,6}\s*category\s+switch\b", re.IGNORECASE | re.MULTILINE),
    ),
    PrimitiveClassRotationDeclaration(
        "primitive_heading",
        re.compile(r"^\s*#{1,6}\s*primitive\s*[:\-—]", re.IGNORECASE | re.MULTILINE),
    ),
    PrimitiveClassRotationDeclaration(
        "architectural_primitive_heading",
        re.compile(
            r"^\s*#{1,6}\s*architectural\s+primitive\s*[:\-—]",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
    PrimitiveClassRotationDeclaration(
        "gate_heading",
        re.compile(r"^\s*#{1,6}\s*gate\s*[:\-—]", re.IGNORECASE | re.MULTILINE),
    ),
    PrimitiveClassRotationDeclaration(
        "decomposition_heading",
        re.compile(r"^\s*#{1,6}\s*decomposition\s*[:\-—]", re.IGNORECASE | re.MULTILINE),
    ),
    PrimitiveClassRotationDeclaration(
        "scaling_law_heading",
        re.compile(r"^\s*#{1,6}\s*scaling\s+law\s*[:\-—]", re.IGNORECASE | re.MULTILINE),
    ),
)


def read_explored_primitive_classes(project_dir: Optional[Path]) -> list[dict[str, Any]]:
    """Read ``workspace/explored_primitive_classes.jsonl`` if present."""

    if project_dir is None:
        return []
    path = Path(project_dir) / "workspace" / "explored_primitive_classes.jsonl"
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            if isinstance(row, dict):
                out.append(row)
    except Exception:  # noqa: BLE001
        return []
    return out


def _repo_root_for_project(project_dir: Path) -> Path:
    return Path(project_dir).parent.parent


def cross_substrate_primitive_class_ledger_path_for_repo(repo_root: Path) -> Path:
    """Canonical cross-substrate primitive-class ledger path."""

    return (
        Path(repo_root)
        / "analytics" / "public" / "queries" / "rd"
        / "cross_substrate_explored_classes.jsonl"
    )


def cross_substrate_primitive_class_ledger_path(project_dir: Path) -> Path:
    """Canonical cross-substrate primitive-class ledger path for a project."""

    return cross_substrate_primitive_class_ledger_path_for_repo(
        _repo_root_for_project(project_dir)
    )


def _legacy_cross_substrate_primitive_class_ledger_path(project_dir: Path) -> Path:
    return (
        _repo_root_for_project(project_dir)
        / "analytics" / "queries" / "cross_substrate_explored_classes.jsonl"
    )


def read_cross_substrate_primitive_classes(project_dir: Optional[Path]) -> list[dict[str, Any]]:
    """Read the cross-substrate primitive-class ledger if present."""

    if project_dir is None:
        return []
    out: list[dict[str, Any]] = []
    ledgers = (
        cross_substrate_primitive_class_ledger_path(Path(project_dir)),
        _legacy_cross_substrate_primitive_class_ledger_path(Path(project_dir)),
    )
    seen: set[str] = set()
    for ledger in ledgers:
        if not ledger.exists():
            continue
        try:
            for line in ledger.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:  # noqa: BLE001
                    continue
                if not isinstance(row, dict):
                    continue
                key = json.dumps(row, sort_keys=True, separators=(",", ":"))
                if key in seen:
                    continue
                seen.add(key)
                out.append(row)
        except Exception:  # noqa: BLE001
            continue
    return out


def summarize_explored_primitive_classes(
    project_dir: Optional[Path],
    *,
    include_cross_substrate: bool = False,
) -> dict[str, Any]:
    """Return per-class summaries for in-loop prompts and out-of-loop RD tools."""

    history = read_explored_primitive_classes(project_dir)
    project_slug = Path(project_dir).name if project_dir else ""
    cross_history = (
        read_cross_substrate_primitive_classes(project_dir)
        if include_cross_substrate
        else []
    )
    cross_other = [
        row for row in cross_history if row.get("project_slug") != project_slug
    ]

    per_class: dict[str, dict[str, Any]] = {}
    for entry in history:
        cls = str(entry.get("class_name") or "unknown_primitive")
        score = entry.get("score") or 0
        try:
            score_f = float(score)
        except (TypeError, ValueError):
            score_f = 0.0
        if cls not in per_class:
            per_class[cls] = {
                "count": 0,
                "best_score": 0.0,
                "iters": [],
                "outcomes": {},
            }
        outcome = str(entry.get("outcome") or "legacy_unspecified")
        per_class[cls]["count"] += 1
        per_class[cls]["best_score"] = max(per_class[cls]["best_score"], score_f)
        per_class[cls]["iters"].append(entry.get("iter"))
        per_class[cls]["outcomes"][outcome] = (
            per_class[cls]["outcomes"].get(outcome, 0) + 1
        )

    cross_per_class: dict[str, dict[str, Any]] = {}
    for entry in cross_other:
        cls = str(entry.get("class_name") or "unknown")
        slug = str(entry.get("project_slug") or "?")
        score = entry.get("score") or 0
        try:
            score_f = float(score)
        except (TypeError, ValueError):
            score_f = 0.0
        if cls not in cross_per_class:
            cross_per_class[cls] = {"best_score": 0.0, "substrates": set()}
        cross_per_class[cls]["substrates"].add(slug)
        cross_per_class[cls]["best_score"] = max(cross_per_class[cls]["best_score"], score_f)

    return {
        "history": history,
        "cross_other": cross_other,
        "per_class": per_class,
        "cross_per_class": cross_per_class,
    }


def append_explored_primitive_class(
    project_dir: Path,
    run_id: str,
    iter_index: int,
    class_name: str,
    score: float,
    *,
    outcome: str = "judged_candidate",
) -> None:
    """Append one primitive-class row to local and cross-substrate ledgers."""

    workspace = Path(project_dir) / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    out_path = workspace / "explored_primitive_classes.jsonl"
    project_slug = Path(project_dir).name
    record = {
        "run_id": str(run_id),
        "iter": int(iter_index),
        "class_name": str(class_name),
        "score": float(score) if score is not None else None,
        "outcome": str(outcome or "judged_candidate"),
        "ts_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
    }
    with out_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    cross_ledger = cross_substrate_primitive_class_ledger_path(project_dir)
    cross_ledger.parent.mkdir(parents=True, exist_ok=True)
    cross_record = {**record, "project_slug": project_slug}
    with cross_ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(cross_record) + "\n")


def should_track_primitive_class_proposal(thesis_text: str) -> bool:
    """Return True when proposal text declares a primitive-class move."""

    return any(
        declaration.pattern.search(thesis_text or "")
        for declaration in _PRIMITIVE_CLASS_ROTATION_DECLARATIONS
    )


def _extract_heading_class(thesis_text: str) -> Optional[str]:
    m = re.search(
        (
            r"^\s*(?:#{0,6}\s*)?(?:Primitive|Structural Mutation|"
            r"Structural Pivot|Category Switch|Architectural Primitive|"
            r"Gate|Decomposition|Scaling Law)[:\s\-—]+(.+?)$"
        ),
        thesis_text[:4000],
        flags=re.MULTILINE | re.IGNORECASE,
    )
    if not m:
        return None
    return m.group(1).strip().strip("\"'").strip()[:80]


def _extract_class_audit(thesis_text: str) -> Optional[str]:
    m = re.search(
        r"target_entity[^:]*:\s*[\"']?([A-Z][A-Za-z0-9_\- ]{3,80})[\"']?",
        thesis_text,
    )
    if m:
        return m.group(1).strip().rstrip("\"',.").strip()
    heading = _extract_heading_class(thesis_text)
    if heading:
        return heading
    m = re.search(r"\b([A-Z]{2,8}[a-z]?(?:[A-Z][A-Za-z]+)*)\b", thesis_text[:800])
    if m:
        return m.group(1).strip()
    return None


def _extract_class_proof_target(thesis_text: str) -> Optional[str]:
    m = re.search(
        r"^##+\s*(?:Lemma|Theorem|Bridge|Kernel|Tactic|Phase \d[A-Z]+)\s*[:\s\-—]+(.+?)$",
        thesis_text[:4000],
        flags=re.MULTILINE,
    )
    if m:
        return m.group(1).strip().strip("\"'").strip()[:80]
    m = re.search(
        r"\b(phase5[a-z]+_[a-z_]+|ns_[a-z_]+_(?:lemma|bridge|theorem|gate))\b",
        thesis_text[:2000],
    )
    if m:
        return m.group(1).strip()
    m = re.search(r"\b([A-Z]{2,8}[a-z]?)\b", thesis_text[:800])
    if m:
        return m.group(1).strip()
    return None


def _extract_class_nd_features(thesis_text: str) -> Optional[str]:
    heading = _extract_heading_class(thesis_text)
    if heading:
        return heading
    m = re.search(
        r"\b((?:[A-Z][a-z]+(?:[- ][A-Z][a-z]+)*)\s+(?:Gate|Primitive|Decomposition))\b",
        thesis_text[:2000],
    )
    if m:
        return m.group(1).strip()
    m = re.search(r"\b([A-Z]{2,8}[a-z]?)\b", thesis_text[:800])
    if m:
        return m.group(1).strip()
    return None


_PROPOSAL_CLASS_REGEX_EXTRACTORS: dict[str, Any] = {
    "audit": _extract_class_audit,
    "proof_target": _extract_class_proof_target,
    "nd_features": _extract_class_nd_features,
}
_PROPOSAL_CLASS_LLM_CACHE: dict[str, str] = {}


def _extract_class_via_llm(
    thesis_text: str, substrate_class: Optional[str] = None
) -> Optional[str]:
    cache_key = hashlib.sha1(thesis_text[:2000].encode("utf-8")).hexdigest()[:16]
    if cache_key in _PROPOSAL_CLASS_LLM_CACHE:
        return _PROPOSAL_CLASS_LLM_CACHE[cache_key]
    try:
        from src.ztare.common.llm_runtime import (
            LLMRuntime, pick_default_model_id_for_scripts,
        )
    except Exception:  # noqa: BLE001
        return None
    model_id = pick_default_model_id_for_scripts()
    if model_id is None:
        return None
    prompt = (
        "Classify the following research-apparatus proposal into a single "
        "canonical class name. The class name must be:\n"
        "  - <=30 characters\n"
        "  - A short identifier: acronym, snake_case, or PascalCase, not prose\n"
        "  - Substrate-class context: " + (substrate_class or "unknown") + "\n\n"
        "Return ONLY the class name on one line. Two variants of the same "
        "primitive should produce the same canonical name.\n\n"
        "Proposal text:\n---\n"
        + thesis_text[:3500]
        + "\n---\n\nClass name:"
    )
    try:
        runtime = LLMRuntime()
        from src.ztare.common.dispatch_model import dispatch_call_text

        resp = dispatch_call_text(
            "proposal_class_extraction",
            prompt,
            llm_response_call=lambda p: runtime.call_text(
                p,
                model_id=model_id,
                max_tokens=40,
                request_label="proposal_class_extraction",
            ),
            timeout_seconds=120,
        )
        text = (resp.text or "").strip()
    except Exception:  # noqa: BLE001
        return None
    if not text:
        return None
    first_line = text.splitlines()[0].strip().strip("\"'.,;:`")
    if not first_line or len(first_line) > 50:
        return None
    canonical = first_line[:30]
    _PROPOSAL_CLASS_LLM_CACHE[cache_key] = canonical
    return canonical


def extract_proposal_class_name(
    thesis_text: str,
    substrate_class: Optional[str] = None,
    *,
    use_llm: bool = True,
) -> Optional[str]:
    """Best-effort canonical class extraction for primitive-class ledgers."""

    if not thesis_text:
        return None
    if use_llm:
        name = _extract_class_via_llm(thesis_text, substrate_class)
        if name:
            return name
    extractor = _PROPOSAL_CLASS_REGEX_EXTRACTORS.get(
        (substrate_class or "").strip().lower(),
        _extract_class_audit,
    )
    return extractor(thesis_text)


extract_primitive_class_name = extract_proposal_class_name


def maybe_track_primitive_class_rotation(
    *,
    rubric_data: Mapping[str, Any],
    project_dir: Path,
    run_id: str,
    iter_index: int,
    thesis_text: str,
    score: Optional[float],
    outcome: str = "judged_candidate",
    use_llm: bool = True,
) -> PrimitiveClassTrackingResult:
    """Track a primitive-class proposal for future in-loop and RD consumers."""

    if not bool(rubric_data.get("enable_primitive_class_rotation", False)):
        return PrimitiveClassTrackingResult(
            enabled=False,
            should_track=False,
            tracked=False,
            class_name=None,
            reason="disabled",
        )

    if not should_track_primitive_class_proposal(thesis_text):
        return PrimitiveClassTrackingResult(
            enabled=True,
            should_track=False,
            tracked=False,
            class_name=None,
            reason="no_primitive_class_declaration",
        )

    cage_meta = rubric_data.get("cage_meta") or {}
    substrate_class = (
        str(cage_meta.get("class") or "") if isinstance(cage_meta, Mapping) else ""
    )
    class_name = extract_proposal_class_name(
        thesis_text or "",
        substrate_class=substrate_class,
        use_llm=use_llm,
    )
    if not class_name:
        class_name = f"unknown_proposal_iter_{iter_index}"

    append_explored_primitive_class(
        project_dir=project_dir,
        run_id=run_id,
        iter_index=iter_index,
        class_name=class_name,
        score=float(score) if score is not None else 0.0,
        outcome=outcome,
    )
    return PrimitiveClassTrackingResult(
        enabled=True,
        should_track=True,
        tracked=True,
        class_name=class_name,
        reason="tracked",
    )
